from pathlib import Path

from generate_rss import TrendingScraper

HERE = Path(__file__).parent
SAMPLE_HTML = (HERE / "sample_trending.html").read_text()


def test_extract_repos():
    scraper = TrendingScraper()
    repos = scraper.extract_repos(SAMPLE_HTML)

    assert len(repos) == 2

    r1 = repos[0]
    assert r1["full_name"] == "owner1/repo1"
    assert r1["url"] == "https://github.com/owner1/repo1"
    assert r1["description"] == "Description of repo 1"
    assert r1["language"] == "Python"
    assert r1["stars_total"] == 1500
    assert r1["forks"] == 300
    assert r1["stars_today"] == 450

    r2 = repos[1]
    assert r2["full_name"] == "owner2/repo2"
    assert r2["url"] == "https://github.com/owner2/repo2"
    assert r2["language"] == "Rust"
    assert r2["stars_total"] == 2500
    assert r2["stars_today"] == 1200


def test_fallback_selectors():
    html = SAMPLE_HTML.replace("article", "div")
    scraper = TrendingScraper()
    repos = scraper.extract_repos(html)
    assert len(repos) == 2


def test_empty_page():
    scraper = TrendingScraper()
    repos = scraper.extract_repos("<html></html>")
    assert repos == []
