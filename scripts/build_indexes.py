#!/usr/bin/env python3
"""Phase 4: Build index pages for each content section."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def build_species_index():
    """Build the species reviews index page with a searchable table."""
    with open(DATA_DIR / "species_list.json") as f:
        species = json.load(f)

    lines = [
        "---",
        "layout: default",
        "title: Species Reviews",
        "parent: FEIS",
        "has_children: true",
        "nav_order: 2",
        "---",
        "",
        "# Species Reviews",
        "",
        f"FEIS contains **{len(species)}** species reviews covering fire effects on plants and animals.",
        "Each review summarizes the available scientific literature on a species' fire ecology,",
        "distribution, botanical and ecological characteristics, and management considerations.",
        "",
        '<input type="text" id="species-search" placeholder="Search by name, abbreviation, or year..." style="width:100%;padding:8px;margin-bottom:12px;border:1px solid #ccc;border-radius:4px;">',
        "",
        "| Abbreviation | Common Name | Scientific Name | Year |",
        "|:-------------|:------------|:----------------|:-----|",
    ]

    for sp in sorted(species, key=lambda x: x.get("common_name", "").lower()):
        abbr = sp.get("abbreviation", sp["slug"].upper())
        common = sp.get("common_name", "")
        scientific = sp.get("scientific_name", "")
        year = sp.get("year", "")
        slug = sp["slug"]
        lines.append(
            f"| [{abbr}]({{{{ site.baseurl }}}}/species-reviews/{slug}) | {common} | *{scientific}* | {year} |"
        )

    # Add search JavaScript
    lines.append("")
    lines.append("<script>")
    lines.append("document.getElementById('species-search').addEventListener('input', function() {")
    lines.append("  var filter = this.value.toLowerCase();")
    lines.append("  var rows = document.querySelectorAll('table tbody tr');")
    lines.append("  rows.forEach(function(row) {")
    lines.append("    var text = row.textContent.toLowerCase();")
    lines.append("    row.style.display = text.includes(filter) ? '' : 'none';")
    lines.append("  });")
    lines.append("});")
    lines.append("</script>")

    output_path = PROJECT_ROOT / "species-reviews" / "index.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    print(f"  Wrote species-reviews/index.md ({len(species)} entries)")


def build_fire_regimes_index():
    """Build the fire regimes index page."""
    with open(DATA_DIR / "fire_regimes_list.json") as f:
        regimes = json.load(f)

    lines = [
        "---",
        "layout: default",
        "title: Fire Regimes",
        "parent: FEIS",
        "has_children: true",
        "nav_order: 3",
        "---",
        "",
        "# Fire Regimes",
        "",
        f"FEIS contains **{len(regimes)}** fire regime publications organized by plant community.",
        "These include full literature syntheses and shorter LANDFIRE-based reports.",
        "",
        "| Title | Type | Year |",
        "|:------|:-----|:-----|",
    ]

    for regime in sorted(regimes, key=lambda x: x.get("title", "").lower()):
        title = regime.get("title", "")
        rtype = regime.get("type", "")
        year = regime.get("year", "")
        slug = regime["slug"]
        lines.append(
            f"| [{title}]({{{{ site.baseurl }}}}/fire-regimes/{slug}) | {rtype} | {year} |"
        )

    output_path = PROJECT_ROOT / "fire-regimes" / "index.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    print(f"  Wrote fire-regimes/index.md ({len(regimes)} entries)")


def build_fire_studies_index():
    """Build the fire studies index page."""
    with open(DATA_DIR / "fire_studies_list.json") as f:
        studies = json.load(f)

    lines = [
        "---",
        "layout: default",
        "title: Fire Studies",
        "parent: FEIS",
        "has_children: true",
        "nav_order: 4",
        "---",
        "",
        "# Fire Studies",
        "",
        f"FEIS contains **{len(studies)}** fire study research project summaries.",
        "",
        "| Title | Authors | Year |",
        "|:------|:--------|:-----|",
    ]

    for study in sorted(studies, key=lambda x: x.get("title", "").lower()):
        title = study.get("title", "")
        authors = study.get("authors", "")
        year = study.get("year", "")
        slug = study["slug"]
        lines.append(
            f"| [{title}]({{{{ site.baseurl }}}}/fire-studies/{slug}) | {authors} | {year} |"
        )

    output_path = PROJECT_ROOT / "fire-studies" / "index.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    print(f"  Wrote fire-studies/index.md ({len(studies)} entries)")


def update_landing_page_counts():
    """Update the landing page with actual content counts."""
    with open(DATA_DIR / "species_list.json") as f:
        species_count = len(json.load(f))
    with open(DATA_DIR / "fire_regimes_list.json") as f:
        regimes_count = len(json.load(f))
    with open(DATA_DIR / "fire_studies_list.json") as f:
        studies_count = len(json.load(f))

    index_path = PROJECT_ROOT / "index.md"
    with open(index_path, "r") as f:
        content = f.read()

    # Update counts in the table
    import re
    content = re.sub(
        r'(\| \[Species Reviews\].*?\| )—( \|)',
        f'\\g<1>{species_count}\\2',
        content
    )
    content = re.sub(
        r'(\| \[Fire Regimes\].*?\| )—( \|)',
        f'\\g<1>{regimes_count}\\2',
        content
    )
    content = re.sub(
        r'(\| \[Fire Studies\].*?\| )—( \|)',
        f'\\g<1>{studies_count}\\2',
        content
    )

    with open(index_path, "w") as f:
        f.write(content)
    print(f"  Updated index.md counts: {species_count} species, {regimes_count} regimes, {studies_count} studies")


def main():
    print("=== Building Index Pages ===")
    build_species_index()
    build_fire_regimes_index()
    build_fire_studies_index()
    update_landing_page_counts()


if __name__ == "__main__":
    main()
