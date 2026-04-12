#!/usr/bin/env python3
"""Phase 3: Convert scraped FEIS HTML to Jekyll Markdown with YAML front matter."""

import json
import os
import re
import sys
import html as html_lib
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag
import html2text

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_HTML_DIR = PROJECT_ROOT / "raw_html"

# html2text converter setup
H2T = html2text.HTML2Text()
H2T.body_width = 0  # no wrapping
H2T.unicode_snob = True
H2T.protect_links = True
H2T.wrap_links = False
H2T.single_line_break = False
H2T.skip_internal_links = False
H2T.ignore_images = False
H2T.default_image_alt = ""


def clean_text(text):
    """Clean up text: normalize whitespace, fix encoding issues."""
    if not text:
        return ""
    # Normalize whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    return text.strip()


def yaml_escape(val):
    """Escape a value for YAML front matter."""
    if val is None:
        return '""'
    val = str(val).strip()
    if not val:
        return '""'
    # Quote if contains special YAML chars
    if any(c in val for c in ':#{}[]&*?|>!%@`\'"'):
        val = val.replace('"', '\\"')
        return f'"{val}"'
    return val


def convert_html_section(section_div, content_type, slug):
    """Convert an accordion section's HTML content to Markdown."""
    if not section_div:
        return ""

    # Fix image paths - ensure USDA URLs are absolute
    for img in section_div.find_all("img"):
        src = img.get("src", "")
        # Convert relative USDA paths to absolute URLs
        if src.startswith("/sites/default/files/"):
            img["src"] = f"https://research.fs.usda.gov{src}"
        # Already-absolute USDA URLs are left as-is

        # Add caption/credit as markdown below image
        caption = img.get("data-caption", "")
        credit = img.get("data-credit", "")
        if caption:
            # Parse HTML in caption
            caption_soup = BeautifulSoup(caption, "html.parser")
            caption_text = caption_soup.get_text(strip=True)
        else:
            caption_text = ""

    html_str = str(section_div)

    # Handle figure captions - wrap img+caption in markdown
    # Convert data-caption and data-credit to visible text
    html_str = re.sub(
        r'<img([^>]*?)data-caption="([^"]*?)"([^>]*?)data-credit="([^"]*?)"([^>]*?)/?>',
        lambda m: _img_with_caption(m),
        html_str
    )
    html_str = re.sub(
        r'<img([^>]*?)data-credit="([^"]*?)"([^>]*?)data-caption="([^"]*?)"([^>]*?)/?>',
        lambda m: _img_with_caption_reversed(m),
        html_str
    )

    md = H2T.handle(html_str)
    md = clean_text(md)
    return md


def _img_with_caption(match):
    """Replace img tag with caption/credit as visible text."""
    pre = match.group(1)
    caption_html = html_lib.unescape(match.group(2))
    mid = match.group(3)
    credit = html_lib.unescape(match.group(4))
    post = match.group(5)

    caption_soup = BeautifulSoup(caption_html, "html.parser")
    caption_text = caption_soup.get_text(strip=True)

    img_tag = f'<img{pre}{mid}{post}/>'
    result = img_tag
    if caption_text:
        result += f'\n<figcaption>{caption_text}'
        if credit:
            result += f' <em>{credit}</em>'
        result += '</figcaption>\n'
    elif credit:
        result += f'\n<figcaption><em>{credit}</em></figcaption>\n'
    return result


def _img_with_caption_reversed(match):
    """Handle reversed order of data-credit and data-caption."""
    pre = match.group(1)
    credit = html_lib.unescape(match.group(2))
    mid = match.group(3)
    caption_html = html_lib.unescape(match.group(4))
    post = match.group(5)

    caption_soup = BeautifulSoup(caption_html, "html.parser")
    caption_text = caption_soup.get_text(strip=True)

    img_tag = f'<img{pre}{mid}{post}/>'
    result = img_tag
    if caption_text:
        result += f'\n<figcaption>{caption_text}'
        if credit:
            result += f' <em>{credit}</em>'
        result += '</figcaption>\n'
    elif credit:
        result += f'\n<figcaption><em>{credit}</em></figcaption>\n'
    return result


def parse_taxonomy(species_div):
    """Parse taxonomy info from the 'Species in This Review' section."""
    taxonomy = {}
    if not species_div:
        return taxonomy

    table = species_div.find("table")
    if not table:
        return taxonomy

    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        # Column 3 has classification info
        class_cell = cells[3]
        class_text = str(class_cell)

        patterns = {
            "life_form": r"Life Form:</strong>\s*([^<]+)",
            "kingdom": r"Kingdom:</strong>\s*([^<]+)",
            "class": r"Class</strong>:\s*([^<]+)",
            "order": r"Order:</strong>\s*([^<]+)",
            "family": r"Family:</strong>\s*([^<]+)",
            "genus": r"Genus:</strong>\s*([^<]+)",
        }
        for key, pattern in patterns.items():
            m = re.search(pattern, class_text)
            if m:
                taxonomy[key] = m.group(1).strip()

        # Column 4 has status info
        if len(cells) > 4:
            status_cell = cells[4]
            status_text = str(status_cell)
            status_patterns = {
                "fed_protected": r"Fed\. Protected:</strong>\s*([^<]+)",
                "nativity": r"Nativity:</strong>\s*([^<]+)",
                "invasiveness": r"Invasiveness:</strong>\s*([^<]+)",
            }
            for key, pattern in status_patterns.items():
                m = re.search(pattern, status_text)
                if m:
                    taxonomy[key] = m.group(1).strip()

        break  # Usually just one data row per species

    return taxonomy


def convert_species_review(slug, listing_info):
    """Convert a species review HTML file to Markdown."""
    html_path = RAW_HTML_DIR / "species-reviews" / f"{slug}.html"
    if not html_path.exists():
        return None

    with open(html_path, "r", encoding="utf-8") as f:
        html_text = f.read()

    soup = BeautifulSoup(html_text, "html.parser")
    article = soup.find("article")
    if not article:
        return None

    # Extract metadata
    written_div = article.find("div", class_="field--name-written-date-field")
    written_date = ""
    if written_div:
        item = written_div.find("div", class_="field__item")
        written_date = item.get_text(strip=True) if item else written_div.get_text(strip=True)
        written_date = written_date.replace("Written", "").strip()

    contrib_div = article.find("div", class_="field--name-contributor-field")
    contributors = ""
    if contrib_div:
        item = contrib_div.find("div", class_="field__item")
        contributors = item.get_text(strip=True) if item else contrib_div.get_text(strip=True)
        contributors = contributors.replace("Contributors", "").strip()

    # Parse taxonomy
    species_div = article.find("div", id="species")
    taxonomy = parse_taxonomy(species_div)

    # Build YAML front matter
    front_matter = {
        "layout": "default",
        "title": f"{listing_info.get('scientific_name', '')} — {listing_info.get('common_name', '')}",
        "abbreviation": listing_info.get("abbreviation", slug.upper()),
        "common_name": listing_info.get("common_name", ""),
        "scientific_name": listing_info.get("scientific_name", ""),
        "parent": "Species Reviews",
        "grand_parent": "FEIS",
        "nav_order": 1,
        "nav_exclude": True,
        "written_date": written_date,
        "contributors": contributors,
        "year": listing_info.get("year", ""),
    }
    front_matter.update(taxonomy)

    # Build markdown
    lines = ["---"]
    for key, val in front_matter.items():
        lines.append(f"{key}: {yaml_escape(val)}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {listing_info.get('scientific_name', slug)} — {listing_info.get('common_name', slug)}")
    lines.append("")

    # Add metadata block
    if written_date:
        lines.append(f"**Written:** {written_date}")
    if contributors:
        lines.append(f"  \n**Contributors:** {contributors}")
    lines.append("")

    # Process each accordion section (skip citation and species-in-review)
    section_order = [
        ("citation", "Citation"),
        ("summary", "Summary"),
        ("image-gallery", "Image Gallery"),
        ("introduction", "Introduction"),
        ("distribution", "Distribution"),
        ("characteristics", "Botanical and Ecological Characteristics"),
        ("management", "Fire Ecology and Management"),
        ("nonfire-management", "Nonfire Management Considerations"),
        ("appendix", "Appendix"),
        ("appendixes", "Appendixes"),
        ("references", "References"),
    ]

    for section_id, section_title in section_order:
        section_div = article.find("div", id=section_id)
        if section_div and len(section_div.get_text(strip=True)) > 0:
            md_content = convert_html_section(section_div, "species-reviews", slug)
            if md_content:
                lines.append(f"## {section_title}")
                lines.append("")
                lines.append(md_content)
                lines.append("")

    return "\n".join(lines)


def convert_fire_regime(slug, listing_info):
    """Convert a fire regime HTML file to Markdown."""
    html_path = RAW_HTML_DIR / "fire-regimes" / f"{slug}.html"
    if not html_path.exists():
        return None

    with open(html_path, "r", encoding="utf-8") as f:
        html_text = f.read()

    soup = BeautifulSoup(html_text, "html.parser")
    article = soup.find("article")
    if not article:
        return None

    written_div = article.find("div", class_="field--name-written-date-field")
    written_date = ""
    if written_div:
        item = written_div.find("div", class_="field__item")
        written_date = item.get_text(strip=True) if item else written_div.get_text(strip=True)
        written_date = written_date.replace("Written", "").strip()

    contrib_div = article.find("div", class_="field--name-contributor-field")
    contributors = ""
    if contrib_div:
        item = contrib_div.find("div", class_="field__item")
        contributors = item.get_text(strip=True) if item else contrib_div.get_text(strip=True)
        contributors = contributors.replace("Contributors", "").strip()

    front_matter = {
        "layout": "default",
        "title": listing_info.get("title", slug),
        "slug": slug,
        "type": listing_info.get("type", ""),
        "parent": "Fire Regimes",
        "grand_parent": "FEIS",
        "nav_order": 1,
        "nav_exclude": True,
        "written_date": written_date,
        "contributors": contributors,
        "year": listing_info.get("year", ""),
    }

    lines = ["---"]
    for key, val in front_matter.items():
        lines.append(f"{key}: {yaml_escape(val)}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {listing_info.get('title', slug)}")
    lines.append("")
    if listing_info.get("type"):
        lines.append(f"**Type:** {listing_info['type']}")
    if written_date:
        lines.append(f"  \n**Written:** {written_date}")
    if contributors:
        lines.append(f"  \n**Contributors:** {contributors}")
    lines.append("")

    # Fire regime sections vary - dynamically discover them
    for acc in article.find_all("div", class_="usa-accordion"):
        heading = acc.find("h4", class_="usa-accordion__heading")
        content_div = acc.find("div", class_="usa-accordion__content")
        if not heading or not content_div:
            continue
        section_title = heading.get_text(strip=True)
        if len(content_div.get_text(strip=True)) > 0:
            md_content = convert_html_section(content_div, "fire-regimes", slug)
            if md_content:
                lines.append(f"## {section_title}")
                lines.append("")
                lines.append(md_content)
                lines.append("")

    return "\n".join(lines)


def convert_fire_study(slug, listing_info):
    """Convert a fire study HTML file to Markdown."""
    html_path = RAW_HTML_DIR / "fire-studies" / f"{slug}.html"
    if not html_path.exists():
        return None

    with open(html_path, "r", encoding="utf-8") as f:
        html_text = f.read()

    soup = BeautifulSoup(html_text, "html.parser")
    article = soup.find("article")
    if not article:
        return None

    written_div = article.find("div", class_="field--name-written-date-field")
    written_date = ""
    if written_div:
        item = written_div.find("div", class_="field__item")
        written_date = item.get_text(strip=True) if item else written_div.get_text(strip=True)
        written_date = written_date.replace("Written", "").strip()

    front_matter = {
        "layout": "default",
        "title": listing_info.get("title", slug),
        "slug": slug,
        "authors": listing_info.get("authors", ""),
        "type": listing_info.get("type", ""),
        "parent": "Fire Studies",
        "grand_parent": "FEIS",
        "nav_order": 1,
        "nav_exclude": True,
        "written_date": written_date,
        "year": listing_info.get("year", ""),
    }

    lines = ["---"]
    for key, val in front_matter.items():
        lines.append(f"{key}: {yaml_escape(val)}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {listing_info.get('title', slug)}")
    lines.append("")
    if listing_info.get("authors"):
        lines.append(f"**Authors:** {listing_info['authors']}")
    if written_date:
        lines.append(f"  \n**Written:** {written_date}")
    lines.append("")

    # Dynamic sections
    for acc in article.find_all("div", class_="usa-accordion"):
        heading = acc.find("h4", class_="usa-accordion__heading")
        content_div = acc.find("div", class_="usa-accordion__content")
        if not heading or not content_div:
            continue
        section_title = heading.get_text(strip=True)
        if len(content_div.get_text(strip=True)) > 0:
            md_content = convert_html_section(content_div, "fire-studies", slug)
            if md_content:
                lines.append(f"## {section_title}")
                lines.append("")
                lines.append(md_content)
                lines.append("")

    return "\n".join(lines)


def convert_glossary():
    """Convert the glossary page to Markdown."""
    html_path = RAW_HTML_DIR / "glossary.html"
    if not html_path.exists():
        print("  Glossary HTML not found, skipping")
        return

    with open(html_path, "r", encoding="utf-8") as f:
        html_text = f.read()

    soup = BeautifulSoup(html_text, "html.parser")
    article = soup.find("article")
    if not article:
        return

    lines = ["---"]
    lines.append("layout: default")
    lines.append("title: Glossary")
    lines.append("parent: FEIS")
    lines.append("nav_order: 5")
    lines.append("---")
    lines.append("")
    lines.append("# FEIS Glossary")
    lines.append("")

    content = article.find("div", class_="fsrd-article__content")
    if content:
        md = H2T.handle(str(content))
        lines.append(clean_text(md))

    output_path = PROJECT_ROOT / "glossary.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("  Wrote glossary.md")


def main():
    content_type = sys.argv[1] if len(sys.argv) > 1 else "all"

    if content_type in ("all", "species-reviews"):
        print("=== Converting Species Reviews ===")
        with open(DATA_DIR / "species_list.json") as f:
            species = json.load(f)
        output_dir = PROJECT_ROOT / "species-reviews"
        output_dir.mkdir(parents=True, exist_ok=True)

        converted = 0
        for item in species:
            slug = item["slug"]
            md = convert_species_review(slug, item)
            if md:
                with open(output_dir / f"{slug}.md", "w", encoding="utf-8") as f:
                    f.write(md)
                converted += 1
        print(f"  Converted {converted}/{len(species)} species reviews")

    if content_type in ("all", "fire-regimes"):
        print("\n=== Converting Fire Regimes ===")
        with open(DATA_DIR / "fire_regimes_list.json") as f:
            regimes = json.load(f)
        output_dir = PROJECT_ROOT / "fire-regimes"
        output_dir.mkdir(parents=True, exist_ok=True)

        converted = 0
        for item in regimes:
            slug = item["slug"]
            md = convert_fire_regime(slug, item)
            if md:
                with open(output_dir / f"{slug}.md", "w", encoding="utf-8") as f:
                    f.write(md)
                converted += 1
        print(f"  Converted {converted}/{len(regimes)} fire regimes")

    if content_type in ("all", "fire-studies"):
        print("\n=== Converting Fire Studies ===")
        with open(DATA_DIR / "fire_studies_list.json") as f:
            studies = json.load(f)
        output_dir = PROJECT_ROOT / "fire-studies"
        output_dir.mkdir(parents=True, exist_ok=True)

        converted = 0
        for item in studies:
            slug = item["slug"]
            md = convert_fire_study(slug, item)
            if md:
                with open(output_dir / f"{slug}.md", "w", encoding="utf-8") as f:
                    f.write(md)
                converted += 1
        print(f"  Converted {converted}/{len(studies)} fire studies")

    if content_type in ("all", "glossary"):
        print("\n=== Converting Glossary ===")
        convert_glossary()


if __name__ == "__main__":
    main()
