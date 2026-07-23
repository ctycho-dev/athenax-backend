from app.common.validators import extract_domain


def test_extract_domain_strips_scheme_and_www():
    assert extract_domain("https://www.athenax.co/about") == "athenax.co"


def test_extract_domain_bare_host():
    assert extract_domain("athenax.co") == "athenax.co"


def test_extract_domain_subdomain_preserved():
    assert extract_domain("http://sub.example.com/x?y=1") == "sub.example.com"


def test_extract_domain_invalid_returns_none():
    assert extract_domain("not a url") is None
    assert extract_domain("") is None
