# GitHub Trending RSS

Scrapes [GitHub Trending](https://github.com/trending) and produces an RSS or Atom feed. Designed to be consumed by [Newsboat](https://newsboat.org/), a cron job, or any RSS reader.

## Requirements

- **Docker** (recommended), or
- **Python 3.10+** with `pip`

## Quick start

```bash
docker build -t gh-trending-rss .
docker run --rm gh-trending-rss > trending.xml
```

Pipe it into a file, a feed reader, or Newsboat directly.

## CLI reference

```
usage: generate_rss.py [-h] [-l LANGUAGE] [-s {daily,weekly,monthly}]
                       [-f {rss,atom}] [-o OUTPUT]

Generate an RSS/Atom feed from GitHub trending repositories.

options:
  -h, --help            show this help message and exit
  -l, --language        Filter by language (e.g., python, rust, typescript)
  -s, --since           Timeframe: daily, weekly, monthly (default: daily)
  -f, --format          Output format: rss, atom (default: rss)
  -o, --output          Write to file instead of stdout
```

### Examples

```bash
# All languages, daily, RSS (defaults)
docker run --rm gh-trending-rss

# Python repos this week, Atom format
docker run --rm gh-trending-rss \
  --language python --since weekly --format atom

# Rust repos, write to file
docker run --rm gh-trending-rss \
  --language rust --output /tmp/rust-trending.xml
```

## Newsboat integration

Add one or more lines to `~/.newsboat/urls`:

```
exec:docker run --rm gh-trending-rss
exec:docker run --rm gh-trending-rss --language python
exec:docker run --rm gh-trending-rss --language rust --since weekly
```

Newsboat calls the container on each refresh and parses the RSS from stdout.

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run directly
python generate_rss.py --language go

# Run tests
pip install pytest
pytest -v
```

### Installing as a pip package

```bash
pip install -e .
gh-trending-rss --language typescript --format atom
```

## Deployment

### 1. Ad-hoc (manual)

```bash
docker build -t gh-trending-rss .
docker run --rm gh-trending-rss --format atom > $(date +%F)-trending.atom
```

### 2. Periodic via cron

```bash
# Download Python trending every hour
0 * * * * docker run --rm gh-trending-rss --language python > $HOME/feeds/python-trending.xml
```

### 3. Periodic via systemd timer

`~/.config/systemd/user/gh-trending-rss.service`:

```ini
[Unit]
Description=GitHub Trending RSS feed

[Service]
Type=oneshot
ExecStart=docker run --rm gh-trending-rss --language python
StandardOutput=file:%h/feeds/python-trending.xml
```

`~/.config/systemd/user/gh-trending-rss.timer`:

```ini
[Unit]
Description=Update GitHub Trending feed hourly

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now gh-trending-rss.timer
```

### 4. Lightweight HTTP server (optional)

Serve the feed over HTTP with a tiny wrapper:

```bash
docker run --rm -p 8080:80 --entrypoint "" python:3.12-slim \
  sh -c "pip install -q $(cat requirements.txt) && \
  python generate_rss.py > /dev/null && \
  python -m http.server 80"
```

*(For production, use a proper scheduler that re-generates the feed and serves it with nginx/Caddy.)*

### 5. OCI image registry (GHCR / Docker Hub)

Build once, pull anywhere:

```bash
docker build -t ghcr.io/yourname/gh-trending-rss:latest .
docker push ghcr.io/yourname/gh-trending-rss:latest

# On another machine:
docker run --rm ghcr.io/yourname/gh-trending-rss --language rust
```

## Architecture

```
GitHub Trending HTML
        │
        ▼
  TrendingScraper.fetch_html()
    └─ requests.Session with urllib3.Retry (3 retries, backoff)
        │
        ▼
  TrendingScraper.extract_repos()
    └─ BeautifulSoup (lxml parser) → list[dict]
    └─ Fallback CSS selectors: article.Box-row → div.Box-row → [class*='Box-row']
        │
        ▼
  build_feed()
    └─ feedgen → RSS 2.0 or Atom 1.0 XML string
        │
        ▼
  stdout / file
```

## Project structure

```
├── generate_rss.py          # CLI entry point, scraper, feed builder
├── requirements.txt         # Python dependencies (pinned ranges)
├── pyproject.toml           # Project metadata, pytest config
├── Dockerfile               # Multi-layer Docker image
├── .dockerignore            # Excludes tests, .git from image
├── .github/workflows/ci.yml # CI: pytest on 3.10–3.12
├── tests/
│   ├── sample_trending.html # Mock GitHub HTML fixture
│   ├── test_parse_int.py    # Number-parsing edge cases
│   ├── test_extract_repos.py# Scraping logic with fallback tests
│   └── test_build_feed.py   # RSS/Atom output structure tests
└── README.md
```

## Testing

```bash
pytest -v              # 14 tests across 3 modules
pytest --cov=. tests/  # with coverage (install pytest-cov)
```

CI runs tests against Python 3.10, 3.11, and 3.12 on every push/PR.

## Troubleshooting

| Symptom | Likely cause |
|---------|-------------|
| `no repositories found` | GitHub changed their HTML markup. Check [GitHub Trending](https://github.com/trending) and update CSS selectors in `extract_repos()`. |
| `403 Forbidden` | Rate-limited. The retry logic handles 502/503/504 but not 403. Add a longer delay or rotate User-Agent. |
| Newsboat shows no items | Ensure the `exec:` command works standalone. The container must output valid RSS to stdout. |
