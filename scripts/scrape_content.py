#!/usr/bin/env python3
"""Phase 2: Scrape all FEIS content pages and download images."""

import json
import os
import re
import sys
import time
import hashlib
import requests
from pathlib import Path
from urllib.parse import urlparse

BASE_URL = "https://research.fs.usda.gov"
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_HTML_DIR = PROJECT_ROOT / "raw_html"
HEADERS = {"User-Agent": "FEIS-Mirror-Bot/1.0 (educational mirror project)"}
DELAY = 0.5  # seconds between requests


def fetch_page(url, retries=3):
    """Fetch a page with rate limiting and retries."""
    for attempt in range(retries):
        try:
            time.sleep(DELAY)
            resp = requests.get(url, headers=HEADERS, timeout=60)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            if attempt < retries - 1:
                print(f"    Retry {attempt + 1} for {url}: {e}")
                time.sleep(2 ** attempt)
            else:
                print(f"    FAILED after {retries} attempts: {url}: {e}")
                return None


def download_image(url, dest_path):
    """Download an image if not already present."""
    if dest_path.exists():
        return True
    try:
        time.sleep(0.2)
        resp = requests.get(url, headers=HEADERS, timeout=60, stream=True)
        resp.raise_for_status()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        return True
    except requests.RequestException as e:
        print(f"    Image download failed: {url}: {e}")
        return False


def extract_images_from_html(html_text, content_type, slug):
    """Find all image URLs in HTML and download them. Returns mapping of old→new paths."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_text, "html.parser")
    article = soup.find("article")
    if not article:
        return {}

    image_map = {}
    images_dir = PROJECT_ROOT / "assets" / "images" / content_type

    # Find all images in the article
    for img in article.find_all("img"):
        src = img.get("src", "")
        if not src or "usda-logo" in src or "fs-logo" in src or "us_flag" in src:
            continue
        if not src.startswith("http"):
            src = BASE_URL + src
        if "research.fs.usda.gov" not in src:
            continue

        # Generate local filename from URL
        parsed = urlparse(src)
        filename = os.path.basename(parsed.path)
        if not filename:
            continue

        # Prefix with slug to avoid collisions
        local_name = f"{slug}_{filename}" if not filename.startswith(f"feis-{slug}") else filename
        dest = images_dir / local_name

        if download_image(src, dest):
            # Store relative path from markdown file location
            rel_path = f"/assets/images/{content_type}/{local_name}"
            image_map[src] = rel_path

    return image_map


def scrape_content_type(content_type, items):
    """Scrape all pages for a content type."""
    output_dir = RAW_HTML_DIR / content_type
    output_dir.mkdir(parents=True, exist_ok=True)

    total = len(items)
    skipped = 0
    failed = 0

    for i, item in enumerate(items):
        slug = item.get("slug") or item.get("abbreviation", "").lower()
        url = item["url"]
        html_path = output_dir / f"{slug}.html"

        # Skip if already scraped
        if html_path.exists() and html_path.stat().st_size > 1000:
            skipped += 1
            continue

        print(f"  [{i+1}/{total}] Scraping {slug}...")
        html = fetch_page(url)
        if html:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            # Download images
            extract_images_from_html(html, content_type, slug)
        else:
            failed += 1

    print(f"  Done: {total - skipped - failed} scraped, {skipped} already cached, {failed} failed")


def scrape_glossary():
    """Scrape the glossary page."""
    output_dir = RAW_HTML_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / "glossary.html"

    if html_path.exists() and html_path.stat().st_size > 1000:
        print("  Glossary already cached")
        return

    print("  Scraping glossary...")
    html = fetch_page(f"{BASE_URL}/feis/glossary")
    if html:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)


def main():
    content_type = sys.argv[1] if len(sys.argv) > 1 else "all"

    if content_type in ("all", "species-reviews"):
        print("=== Scraping Species Reviews ===")
        with open(DATA_DIR / "species_list.json") as f:
            species = json.load(f)
        scrape_content_type("species-reviews", species)

    if content_type in ("all", "fire-regimes"):
        print("\n=== Scraping Fire Regimes ===")
        with open(DATA_DIR / "fire_regimes_list.json") as f:
            regimes = json.load(f)
        scrape_content_type("fire-regimes", regimes)

    if content_type in ("all", "fire-studies"):
        print("\n=== Scraping Fire Studies ===")
        with open(DATA_DIR / "fire_studies_list.json") as f:
            studies = json.load(f)
        scrape_content_type("fire-studies", studies)

    if content_type in ("all", "glossary"):
        print("\n=== Scraping Glossary ===")
        scrape_glossary()


if __name__ == "__main__":
    main()
