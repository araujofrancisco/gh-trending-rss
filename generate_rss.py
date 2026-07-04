"""Generate RSS/Atom feeds from GitHub Trending repositories.

Scrapes https://github.com/trending, extracts repository metadata
(name, description, language, stars, forks, daily stars), and outputs
a standards-compliant RSS 2.0 or Atom 1.0 feed to stdout or a file.

Dependencies: requests, beautifulsoup4, feedgen, lxml
"""

import argparse
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://github.com"
TRENDING_URL = urljoin(BASE_URL, "/trending")
USER_AGENT = "Mozilla/5.0 (compatible; gh-trending-rss/1.0)"

SINCE_CHOICES = ["daily", "weekly", "monthly"]
FORMAT_CHOICES = ["rss", "atom"]


def parse_int(text: str) -> int:
    """Parse a GitHub-formatted number string into an integer.

    Handles comma separators (``1,234``), ``k``/``K`` suffixes
    (``1.5k`` → 1500), and ``m``/``M`` suffixes (``2.5m`` → 2500000).
    Also handles raw text like ``"123 stars today"`` after the caller
    strips the label.

    Args:
        text: Raw string from the page, possibly empty or ``None``.

    Returns:
        Integer value, or ``0`` if the input cannot be parsed.
    """
    if not text:
        return 0
    text = text.strip().lower().replace(",", "")
    m = re.search(r"([\d.]+)\s*([km]?)", text)
    if not m:
        return 0
    num = float(m.group(1))
    suffix = m.group(2)
    if suffix == "k":
        num *= 1000
    elif suffix == "m":
        num *= 1000000
    return int(num)


class TrendingScraper:
    """Fetch and parse GitHub Trending HTML into structured repository data.

    Uses ``requests`` with automatic retry on transient server errors and
    ``BeautifulSoup`` with the ``lxml`` parser for fast HTML extraction.

    Attributes:
        language: Programming language filter (e.g. ``"python"``) or ``None``.
        since: Trending window — ``"daily"``, ``"weekly"``, or ``"monthly"``.
    """

    def __init__(self, language=None, since="daily"):
        """Args:
            language: Filter results to a specific language (e.g. ``"rust"``).
            since: Time window for trending data.
        """
        self.language = language
        self.since = since
        self._session = self._build_session()

    @property
    def trending_url(self) -> str:
        """Build the GitHub Trending URL for the configured language and window.

        Returns:
            Full URL string, e.g. ``https://github.com/trending/python``.
        """
        url = TRENDING_URL
        if self.language:
            url = f"{url}/{self.language}"
        return url

    def _build_session(self) -> requests.Session:
        """Create a pre-configured ``requests.Session`` with retry logic.

        Retries up to 3 times with exponential backoff on HTTP 502, 503,
        and 504 responses.

        Returns:
            Configured ``requests.Session`` instance.
        """
        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("https://", adapter)
        return session

    def fetch_html(self) -> str:
        """Fetch the GitHub Trending page HTML.

        Sends a ``GET`` request with the configured ``since`` parameter.

        Returns:
            Raw HTML content of the trending page.

        Raises:
            requests.RequestException: If the request fails after all retries.
        """
        params = {"since": self.since}
        r = self._session.get(self.trending_url, params=params, timeout=30)
        r.raise_for_status()
        return r.text

    def extract_repos(self, html: str) -> list[dict]:
        """Parse repository entries from the GitHub Trending HTML.

        Uses a cascade of CSS selectors to handle minor markup changes
        (``article.Box-row`` → ``div.Box-row`` → ``[class*='Box-row']``).

        Args:
            html: Raw HTML of the GitHub Trending page.

        Returns:
            List of dicts with keys ``full_name``, ``url``, ``description``,
            ``language``, ``stars_total``, ``forks``, ``stars_today``.
        """
        soup = BeautifulSoup(html, "lxml")
        repos = []

        articles = soup.select("article.Box-row")
        if not articles:
            articles = soup.select("div.Box-row")
        if not articles:
            articles = soup.select("[class*='Box-row']")

        for article in articles:
            h2 = article.select_one("h2")
            if not h2:
                continue
            a = h2.select_one("a")
            if not a or not a.get("href"):
                continue

            full_name = a.get_text(" ", strip=True).replace(" / ", "/").replace(" ", "")
            href = urljoin(BASE_URL, a["href"].strip())

            desc_el = article.select_one("p")
            description = desc_el.get_text(" ", strip=True) if desc_el else ""

            lang_el = article.select_one('[itemprop="programmingLanguage"]')
            language = lang_el.get_text(" ", strip=True) if lang_el else ""

            stars_total = 0
            forks = 0
            stars_today = 0

            for link in article.select("a"):
                txt = link.get_text(" ", strip=True)
                href2 = link.get("href", "")
                if href2.endswith("/stargazers"):
                    stars_total = parse_int(txt)
                elif href2.endswith("/network/members"):
                    forks = parse_int(txt)
                elif "stars today" in txt.lower():
                    stars_today = parse_int(
                        txt.lower().replace("stars today", "").strip()
                    )

            repos.append(
                {
                    "full_name": full_name,
                    "url": href,
                    "description": description,
                    "language": language,
                    "stars_total": stars_total,
                    "forks": forks,
                    "stars_today": stars_today,
                }
            )

        return repos


def build_feed(repos: list[dict], feed_format="rss", feed_url=None) -> str:
    """Generate an RSS 2.0 or Atom 1.0 feed from parsed repository data.

    Args:
        repos: List of repo dicts from :meth:`TrendingScraper.extract_repos`.
        feed_format: ``"rss"`` or ``"atom"``.
        feed_url: Canonical URL for the feed's ``rel="self"`` link.
            Defaults to the generic trending URL.

    Returns:
        XML feed as a UTF-8 encoded string.
    """
    fg = FeedGenerator()
    fg.id(feed_url or TRENDING_URL)
    fg.title("GitHub Trending")
    fg.link(href=feed_url or TRENDING_URL, rel="alternate")
    fg.link(href=feed_url or TRENDING_URL, rel="self")
    fg.description("Trending repositories from GitHub")
    fg.language("en")
    fg.lastBuildDate(datetime.now(timezone.utc))

    for repo in repos:
        fe = fg.add_entry()
        fe.id(repo["url"])
        fe.title(repo["full_name"])
        fe.link(href=repo["url"])
        desc = repo["description"] or "No description"
        fe.description(
            f'{desc}\n\nLanguage: {repo["language"] or "Unknown"}\n'
            f'Stars: {repo["stars_total"]}\n'
            f'Forks: {repo["forks"]}\n'
            f'Stars today: {repo["stars_today"]}'
        )
        fe.pubDate(datetime.now(timezone.utc))

    if feed_format == "atom":
        return fg.atom_str(pretty=True).decode("utf-8")
    return fg.rss_str(pretty=True).decode("utf-8")


def main():
    """Entry point: parse CLI args, fetch, extract, build feed, and output."""
    parser = argparse.ArgumentParser(
        description="Generate an RSS/Atom feed from GitHub trending repositories."
    )
    parser.add_argument(
        "-l",
        "--language",
        help="Filter by programming language (e.g., python, rust, typescript)",
        default=None,
    )
    parser.add_argument(
        "-s",
        "--since",
        choices=SINCE_CHOICES,
        default="daily",
        help="Trending timeframe (default: daily)",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=FORMAT_CHOICES,
        default="rss",
        help="Feed output format (default: rss)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file path (default: stdout)",
        default=None,
    )
    args = parser.parse_args()

    scraper = TrendingScraper(language=args.language, since=args.since)
    html = scraper.fetch_html()
    repos = scraper.extract_repos(html)

    if not repos:
        print(
            "Error: no repositories found. GitHub markup may have changed.",
            file=sys.stderr,
        )
        sys.exit(1)

    feed = build_feed(repos, feed_format=args.format, feed_url=scraper.trending_url)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(feed)
        print(f"Feed written to {args.output}", file=sys.stderr)
    else:
        print(feed)


if __name__ == "__main__":
    main()
