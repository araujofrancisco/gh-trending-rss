from generate_rss import build_feed

SAMPLE_REPOS = [
    {
        "full_name": "owner1/repo1",
        "url": "https://github.com/owner1/repo1",
        "description": "A test repo",
        "language": "Python",
        "stars_total": 1500,
        "forks": 300,
        "stars_today": 100,
    },
    {
        "full_name": "owner2/repo2",
        "url": "https://github.com/owner2/repo2",
        "description": "",
        "language": "Rust",
        "stars_total": 2500,
        "forks": 500,
        "stars_today": 200,
    },
]


def test_rss_feed():
    feed = build_feed(SAMPLE_REPOS, feed_format="rss")
    assert feed.startswith("<?xml")
    assert "<rss" in feed
    assert "owner1/repo1" in feed
    assert "owner2/repo2" in feed
    assert "A test repo" in feed
    assert "No description" in feed
    assert "Python" in feed
    assert "Rust" in feed


def test_atom_feed():
    feed = build_feed(SAMPLE_REPOS, feed_format="atom")
    assert feed.startswith("<?xml")
    assert "<feed" in feed
    assert "owner1/repo1" in feed


def test_feed_contains_stars():
    feed = build_feed(SAMPLE_REPOS, feed_format="rss")
    assert "Stars: 1500" in feed
    assert "Stars today: 100" in feed
    assert "Forks: 300" in feed


def test_feed_has_self_link():
    url = "https://github.com/trending/python"
    feed = build_feed(SAMPLE_REPOS, feed_format="rss", feed_url=url)
    assert url in feed
