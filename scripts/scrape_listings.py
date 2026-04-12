#!/usr/bin/env python3
"""Phase 1: Scrape FEIS listing pages to build master content lists."""

import json
import os
import re
import time
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://research.fs.usda.gov"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
HEADERS = {"User-Agent": "FEIS-Mirror-Bot/1.0 (educational mirror project)"}


def fetch_page(url):
    """Fetch a page with rate limiting."""
    time.sleep(0.5)
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_species_listings():
    """Scrape all pages of the species reviews listing."""
    species = []
    page = 0
    while True:
        url = f"{BASE_URL}/feis/species-reviews?items_per_page=50&page={page}"
        print(f"  Fetching species page {page}...")
        html = fetch_page(url)
        soup = BeautifulSoup(html, "html.parser")

        # Find the table rows - the listing uses a views table
        table = soup.find("table")
        if not table:
            break

        rows = table.find_all("tr")
        found = 0
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            # Column 0: Abbreviation with link
            link = cells[0].find("a")
            if not link:
                continue
            href = link.get("href", "")
            slug = href.rstrip("/").split("/")[-1]
            abbreviation = cells[0].get_text(strip=True)

            # Column 1: Common Title
            common_name = cells[1].get_text(strip=True)

            # Column 2: Scientific Title
            scientific_name = cells[2].get_text(strip=True)

            # Column 3: Year
            year = cells[3].get_text(strip=True)

            species.append({
                "abbreviation": abbreviation,
                "slug": slug,
                "common_name": common_name,
                "scientific_name": scientific_name,
                "year": year,
                "url": f"{BASE_URL}{href}",
            })
            found += 1

        if found == 0:
            break
        page += 1

    return species


def parse_fire_regime_listings():
    """Scrape all pages of the fire regimes listing."""
    regimes = []
    page = 0
    while True:
        url = f"{BASE_URL}/feis/fire-regimes?items_per_page=50&page={page}"
        print(f"  Fetching fire regimes page {page}...")
        html = fetch_page(url)
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
            title = cells[0].get_text(strip=True)
            regime_type = cells[1].get_text(strip=True)
            year = cells[2].get_text(strip=True)

            regimes.append({
                "title": title,
                "slug": slug,
                "type": regime_type,
                "year": year,
                "url": f"{BASE_URL}{href}",
            })
            found += 1

        if found == 0:
            break
        page += 1

    return regimes


def parse_fire_study_listings():
    """Scrape the fire studies listing (single page)."""
    studies = []
    url = f"{BASE_URL}/feis/fire-studies?items_per_page=50"
    print("  Fetching fire studies page...")
    html = fetch_page(url)
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table")
    if not table:
        return studies

    rows = table.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        link = cells[0].find("a")
        if not link:
            continue
        href = link.get("href", "")
        slug = href.rstrip("/").split("/")[-1]
        title = cells[0].get_text(strip=True)
        authors = cells[1].get_text(strip=True)
        study_type = cells[2].get_text(strip=True)
        year = cells[3].get_text(strip=True)

        studies.append({
            "title": title,
            "slug": slug,
            "authors": authors,
            "type": study_type,
            "year": year,
            "url": f"{BASE_URL}{href}",
        })

    return studies


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    print("=== Parsing Species Reviews Listing ===")
    species = parse_species_listings()
    with open(os.path.join(DATA_DIR, "species_list.json"), "w") as f:
        json.dump(species, f, indent=2)
    print(f"  Found {len(species)} species reviews")

    print("\n=== Parsing Fire Regimes Listing ===")
    regimes = parse_fire_regime_listings()
    with open(os.path.join(DATA_DIR, "fire_regimes_list.json"), "w") as f:
        json.dump(regimes, f, indent=2)
    print(f"  Found {len(regimes)} fire regimes")

    print("\n=== Parsing Fire Studies Listing ===")
    studies = parse_fire_study_listings()
    with open(os.path.join(DATA_DIR, "fire_studies_list.json"), "w") as f:
        json.dump(studies, f, indent=2)
    print(f"  Found {len(studies)} fire studies")

    print(f"\nTotal content pages: {len(species) + len(regimes) + len(studies)}")


if __name__ == "__main__":
    main()
