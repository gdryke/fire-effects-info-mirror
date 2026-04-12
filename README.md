# Fire Effects Information System (FEIS) Mirror

A GitHub Pages mirror of the USDA Forest Service [Fire Effects Information System](https://research.fs.usda.gov/feis) (FEIS), preserving fire ecology reference content in an accessible, searchable format.

## Content

- **1,092 Species Reviews** — Fire ecology information for plants and animals
- **154 Fire Regimes** — Ecosystem-level fire regime descriptions
- **10 Fire Studies** — Research project summaries
- **Glossary** — FEIS terminology

## How It Works

- Content is scraped from `research.fs.usda.gov/feis` and converted to Markdown
- Built with [Jekyll](https://jekyllrb.com/) and the [just-the-docs](https://just-the-docs.github.io/just-the-docs/) theme
- Deployed automatically via GitHub Pages
- A weekly sync workflow checks for new or updated content

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/scrape_listings.py` | Parse listing pages to build content inventories |
| `scripts/scrape_content.py` | Fetch raw HTML and download images |
| `scripts/convert_to_markdown.py` | Convert HTML to Markdown with YAML front matter |
| `scripts/build_indexes.py` | Generate searchable index pages |
| `scripts/sync_feis.py` | Weekly sync — detect new/updated content |

## Local Development

```bash
# Python scraping tools
python -m venv .venv && source .venv/bin/activate
pip install beautifulsoup4 requests html2text

# Jekyll
bundle install
bundle exec jekyll serve
```

## License

FEIS content is produced by the USDA Forest Service and is in the **public domain**.
