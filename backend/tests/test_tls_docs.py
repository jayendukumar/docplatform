from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_tls_install_reference_contains_proxy_and_secure_cookie_contract():
    guide = (ROOT / "docs" / "tls.md").read_text(encoding="utf-8")
    assert "## Caddy" in guide
    assert "## Nginx" in guide
    assert "DOCPLATFORM_SECURE_COOKIES=true" in guide
    assert "proxy_pass http://127.0.0.1:8001" in guide
    assert "does not claim" in guide
