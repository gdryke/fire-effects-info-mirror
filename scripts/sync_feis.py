#!/usr/bin/env python3
"""Phase 6: Weekly sync script — checks for new or updated FEIS content."""

import json
import os
import re
import sys
import time
import requests
from pathlib import Path
from bs4 import BeautifulSoup

# When run from GitHub Actions, scripts/ is in the repo root
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_HTML_DIR = PROJECT_ROOT / "raw_html"

BASE_URL = "https://research.fs.usda.gov"
HEADERS = {"User-Agent": "FEIS-Mirror-Bot/1.0 (educational mirror project)"}
DELAY = 0.5

# Import helpers from other scripts
sys.path.insert(0, str(SCRIPT_DIR))


def fetch_page(url, retries=3):
    for attempt in range(retries):
        try:
            time.sleep(DELAY)
            resp = requests.get(url, headers=HEADERS, timeout=60)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"  FAILED: {url}: {e}")
                return None


def fetch_current_listings(content_type):
    """Fetch current listing pages from FEIS and return items."""
    if content_type == "species-reviews":
        path = "/feis/species-reviews"
    elif content_type == "fire-regimes":
        path = "/feis/fire-regimes"
    elif content_type == "fire-studies":
        path = "/feis/fire-studies"
    else:
        return []

    items = []
    page = 0
    while True:
        url = f"{BASE_URL}{path}?items_per_page=50&page={page}"
        html = fetch_page(url)
        if not html:
            break

        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            break

        rows = table.find_all("tr")
        found = 0
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 3:
                continue
            link = cells[0].find("a")
            if not link:
                continue
            href = link.get("href", "")
            slug = href.rstrip("/").split("/")[-1]

            item = {"slug": slug, "url": f"{BASE_URL}{href}"}

            if content_type == "species-reviews":
                if len(cells) >= 4:
                    item["abbreviation"] = cells[0].get_text(strip=True)
                    item["common_name"] = cells[1].get_text(strip=True)
                    item["scientific_name"] = cells[2].get_text(strip=True)
                    item["year"] = cells[3].get_text(strip=True)
            elif content_type == "fire-regimes":
                item["title"] = cells[0].get_text(strip=True)
                item["type"] = cells[1].get_text(strip=True)
                item["year"] = cells[2].get_text(strip=True)
            elif content_type == "fire-studies":
                if len(cells) >= 4:
                    item["title"] = cells[0].get_text(strip=True)
                    item["authors"] = cells[1].get_text(strip=True)
                    item["type"] = cells[2].get_text(strip=True)
                    item["year"] = cells[3].get_text(strip=True)

            items.append(item)
            found += 1

        if found == 0:
            break
        page += 1

    return items


def find_new_entries(content_type):
    """Compare current listings against saved data to find new entries."""
    # Map content type to data file
    data_files = {
        "species-reviews": "species_list.json",
        "fire-regimes": "fire_regimes_list.json",
        "fire-studies": "fire_studies_list.json",
    }

    data_file = DATA_DIR / data_files[content_type]
    if data_file.exists():
        with open(data_file) as f:
            existing = json.load(f)
        existing_slugs = {item["slug"] for item in existing}
    else:
        existing = []
        existing_slugs = set()

    print(f"\n=== Checking {content_type} ===")
    current = fetch_current_listings(content_type)
    print(f"  Found {len(current)} entries on site, {len(existing_slugs)} in our data")

    new_items = [item for item in current if item["slug"] not in existing_slugs]

    if new_items:
        print(f"  ** {len(new_items)} NEW entries found:")
        for item in new_items:
            print(f"    - {item['slug']}")

        # Update the data file with all current items
        with open(data_file, "w") as f:
            json.dump(current, f, indent=2)
    else:
        print("  No new entries found")

    return new_items


def scrape_and_convert_new(content_type, new_items):
    """Scrape and convert new entries."""
    from scrape_content import fetch_page as scrape_fetch, extract_images_from_html
    from convert_to_markdown import (
        convert_species_review,
        convert_fire_regime,
        convert_fire_study,
    )

    raw_dir = RAW_HTML_DIR / content_type
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_dir = PROJECT_ROOT / content_type.replace("-", "-")
    output_dir.mkdir(parents=True, exist_ok=True)

    for item in new_items:
        slug = item.get("slug") or item.get("abbreviation", "").lower()
        url = item["url"]
        print(f"  Scraping and converting {slug}...")

        # Scrape
        html = scrape_fetch(url)
        if not html:
            continue
        html_path = raw_dir / f"{slug}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        # Download images
        extract_images_from_html(html, content_type, slug)

        # Convert
        if content_type == "species-reviews":
            md = convert_species_review(slug, item)
        elif content_type == "fire-regimes":
            md = convert_fire_regime(slug, item)
        elif content_type == "fire-studies":
            md = convert_fire_study(slug, item)
        else:
            continue

        if md:
            md_path = output_dir / f"{slug}.md"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"    Wrote {md_path.name}")


def rebuild_indexes():
    """Rebuild index pages after adding new content."""
    from build_indexes import main as build_main
    build_main()


def main():
    changes = False

    for content_type in ["species-reviews", "fire-regimes", "fire-studies"]:
        new_items = find_new_entries(content_type)
        if new_items:
            changes = True
            scrape_and_convert_new(content_type, new_items)

    if changes:
        print("\n=== Rebuilding Index Pages ===")
        rebuild_indexes()
        print("\n✅ Sync complete — new content added!")
    else:
        print("\n✅ Sync complete — no changes detected.")


if __name__ == "__main__":
    main()
