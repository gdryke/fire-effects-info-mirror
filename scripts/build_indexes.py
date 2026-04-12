#!/usr/bin/env python3
"""Phase 4: Build index pages for each content section."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def build_species_index():
    """Build the species reviews index page with paginated, searchable table."""
    with open(DATA_DIR / "species_list.json") as f:
        species = json.load(f)

    sorted_species = sorted(species, key=lambda x: x.get("common_name", "").lower())

    # Build compact JSON array for client-side rendering
    species_data = []
    for sp in sorted_species:
        species_data.append({
            "a": sp.get("abbreviation", sp["slug"].upper()),
            "c": sp.get("common_name", ""),
            "s": sp.get("scientific_name", ""),
            "y": sp.get("year", ""),
            "k": sp["slug"],
        })

    species_json = json.dumps(species_data, separators=(",", ":"))

    content = f"""---
layout: default
title: Species Reviews
parent: FEIS
has_children: true
nav_order: 2
---

# Species Reviews

FEIS contains **{len(species)}** species reviews covering fire effects on plants and animals.
Each review summarizes the available scientific literature on a species' fire ecology,
distribution, botanical and ecological characteristics, and management considerations.

<div id="species-app">
<input type="text" id="species-search" placeholder="Search by name, abbreviation, or year..." style="width:100%;padding:8px;margin-bottom:12px;border:1px solid #ccc;border-radius:4px;">

<div id="species-info" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;font-size:0.9em;color:#666;">
  <span id="species-count"></span>
  <span>
    Show
    <select id="per-page" style="padding:2px 4px;border:1px solid #ccc;border-radius:3px;">
      <option value="50" selected>50</option>
      <option value="100">100</option>
      <option value="250">250</option>
      <option value="0">All</option>
    </select>
    per page
  </span>
</div>

<table id="species-table">
<thead><tr><th style="text-align:left">Abbreviation</th><th style="text-align:left">Common Name</th><th style="text-align:left">Scientific Name</th><th style="text-align:left">Year</th></tr></thead>
<tbody id="species-tbody"></tbody>
</table>

<div id="pagination" style="display:flex;justify-content:center;align-items:center;gap:8px;margin-top:16px;flex-wrap:wrap;"></div>
</div>

<script>
(function() {{
  var BASE = "{{{{ site.baseurl }}}}";
  var DATA = {species_json};
  var perPage = 50;
  var currentPage = 1;
  var filtered = DATA;

  var searchEl = document.getElementById("species-search");
  var tbody = document.getElementById("species-tbody");
  var pagEl = document.getElementById("pagination");
  var countEl = document.getElementById("species-count");
  var ppEl = document.getElementById("per-page");

  function render() {{
    var start = perPage > 0 ? (currentPage - 1) * perPage : 0;
    var end = perPage > 0 ? start + perPage : filtered.length;
    var page = filtered.slice(start, end);
    var html = "";
    for (var i = 0; i < page.length; i++) {{
      var d = page[i];
      html += "<tr><td><a href=\\"" + BASE + "/species-reviews/" + d.k + "\\">" + d.a + "</a></td>"
            + "<td>" + d.c + "</td>"
            + "<td><em>" + d.s + "</em></td>"
            + "<td>" + d.y + "</td></tr>";
    }}
    tbody.innerHTML = html;

    var totalPages = perPage > 0 ? Math.ceil(filtered.length / perPage) : 1;
    countEl.textContent = "Showing " + (filtered.length === DATA.length ? "all " + DATA.length : filtered.length + " of " + DATA.length) + " species";

    if (totalPages <= 1) {{ pagEl.innerHTML = ""; return; }}

    var ph = "";
    ph += '<button class="pg-btn" data-p="prev" ' + (currentPage === 1 ? "disabled" : "") + '>&laquo; Prev</button>';

    var pages = getPageNumbers(currentPage, totalPages);
    for (var j = 0; j < pages.length; j++) {{
      if (pages[j] === "...") {{
        ph += '<span style="padding:4px">...</span>';
      }} else {{
        ph += '<button class="pg-btn" data-p="' + pages[j] + '"'
            + (pages[j] === currentPage ? ' style="font-weight:bold;text-decoration:underline;"' : '')
            + '>' + pages[j] + '</button>';
      }}
    }}

    ph += '<button class="pg-btn" data-p="next" ' + (currentPage === totalPages ? "disabled" : "") + '>Next &raquo;</button>';
    pagEl.innerHTML = ph;
  }}

  function getPageNumbers(cur, total) {{
    if (total <= 7) {{ var a=[]; for(var i=1;i<=total;i++) a.push(i); return a; }}
    var pages = [1];
    if (cur > 3) pages.push("...");
    for (var i = Math.max(2, cur-1); i <= Math.min(total-1, cur+1); i++) pages.push(i);
    if (cur < total-2) pages.push("...");
    pages.push(total);
    return pages;
  }}

  searchEl.addEventListener("input", function() {{
    var q = this.value.toLowerCase();
    if (!q) {{ filtered = DATA; }}
    else {{ filtered = DATA.filter(function(d) {{
      return d.a.toLowerCase().indexOf(q) >= 0 || d.c.toLowerCase().indexOf(q) >= 0
          || d.s.toLowerCase().indexOf(q) >= 0 || String(d.y).indexOf(q) >= 0;
    }}); }}
    currentPage = 1;
    render();
  }});

  pagEl.addEventListener("click", function(e) {{
    var btn = e.target.closest(".pg-btn");
    if (!btn || btn.disabled) return;
    var p = btn.dataset.p;
    var totalPages = Math.ceil(filtered.length / perPage);
    if (p === "prev") currentPage = Math.max(1, currentPage - 1);
    else if (p === "next") currentPage = Math.min(totalPages, currentPage + 1);
    else currentPage = parseInt(p);
    render();
    document.getElementById("species-app").scrollIntoView({{ behavior: "smooth" }});
  }});

  ppEl.addEventListener("change", function() {{
    perPage = parseInt(this.value);
    currentPage = 1;
    render();
  }});

  render();
}})();
</script>

<style>
#species-table {{ width:100%; border-collapse:collapse; }}
#species-table th, #species-table td {{ padding:6px 10px; border-bottom:1px solid #eee; }}
#species-table th {{ border-bottom:2px solid #ccc; }}
#species-table tr:hover {{ background:#f8f8f8; }}
.pg-btn {{ padding:4px 10px; border:1px solid #ccc; border-radius:3px; background:#fff; cursor:pointer; font-size:0.9em; }}
.pg-btn:hover:not([disabled]) {{ background:#e8e8e8; }}
.pg-btn[disabled] {{ opacity:0.4; cursor:default; }}
</style>
"""

    output_path = PROJECT_ROOT / "species-reviews" / "index.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(content)
    print(f"  Wrote species-reviews/index.md ({len(species)} entries, paginated)")


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
