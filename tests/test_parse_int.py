from generate_rss import parse_int


def test_empty():
    assert parse_int("") == 0
    assert parse_int(None) == 0


def test_plain_number():
    assert parse_int("42") == 42
    assert parse_int("0") == 0
    assert parse_int("1000") == 1000


def test_with_commas():
    assert parse_int("1,234") == 1234
    assert parse_int("12,345,678") == 12345678


def test_k_suffix():
    assert parse_int("1k") == 1000
    assert parse_int("1.5k") == 1500
    assert parse_int("12.3k") == 12300


def test_m_suffix():
    assert parse_int("1m") == 1000000
    assert parse_int("2.5m") == 2500000


def test_whitespace_and_case():
    assert parse_int("  1.2k  ") == 1200
    assert parse_int("1K") == 1000
    assert parse_int("1M") == 1000000


def test_stars_today_input():
    result = parse_int("123 stars today".lower().replace("stars today", "").strip())
    assert result == 123

    result = parse_int("1.2k stars today".lower().replace("stars today", "").strip())
    assert result == 1200
