from aion.config import resolve_app_host


def test_resolve_app_host_defaults_to_loopback():
    assert resolve_app_host({}) == "127.0.0.1"


def test_resolve_app_host_allows_explicit_override():
    assert resolve_app_host({"APP_HOST": "0.0.0.0"}) == "0.0.0.0"


def test_resolve_app_host_ignores_blank_override():
    assert resolve_app_host({"APP_HOST": "   "}) == "127.0.0.1"
