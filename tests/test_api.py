import importlib

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client(monkeypatch):
    # main keeps links in module-level globals: start every test from a clean slate.
    monkeypatch.setattr(main, "links", {})
    monkeypatch.setattr(main, "url_id", 0)
    monkeypatch.setattr(main, "BASE_URL", "http://test")
    return TestClient(main.app)


def shorten(client, url):
    response = client.post("/", json={"url": url})
    assert response.status_code == 200
    return response.json()["url"]


def hash_of(short_url):
    return short_url.rsplit("/", 1)[1]


def test_post_returns_short_url(client):
    short = shorten(client, "https://example.com/page")
    assert short == f"http://test/{main.encoder.encode(1)}"


def test_post_same_url_returns_same_hash(client):
    first = shorten(client, "https://example.com/page")
    second = shorten(client, "https://example.com/page")
    assert first == second


def test_post_different_urls_return_different_hashes(client):
    first = shorten(client, "https://example.com/a")
    second = shorten(client, "https://example.com/b")
    assert first != second


@pytest.mark.parametrize("url", ["not a url", "ftp://example.com", ""])
def test_post_invalid_url_rejected(client, url):
    response = client.post("/", json={"url": url})
    assert response.status_code == 422


def test_post_missing_url_rejected(client):
    response = client.post("/", json={})
    assert response.status_code == 422


def test_get_redirects_to_original_url(client):
    short = shorten(client, "https://example.com/page?q=1")
    response = client.get(f"/{hash_of(short)}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/page?q=1"


def test_get_unknown_hash_returns_404(client):
    response = client.get("/unknown", follow_redirects=False)
    assert response.status_code == 404


@pytest.fixture
def reload_main(monkeypatch):
    # BASE_URL is read at import time, so the module has to be re-imported.
    def _reload(base_url):
        if base_url is None:
            monkeypatch.delenv("BASE_URL", raising=False)
        else:
            monkeypatch.setenv("BASE_URL", base_url)
        return importlib.reload(main)

    yield _reload
    monkeypatch.undo()
    importlib.reload(main)


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        pytest.param(None, "http://localhost:8000", id="unset"),
        pytest.param("", "http://localhost:8000", id="empty"),
        pytest.param("https://sho.rt", "https://sho.rt", id="set"),
        pytest.param("https://sho.rt/", "https://sho.rt", id="trailing-slash"),
    ],
)
def test_base_url_from_env(reload_main, env, expected):
    assert reload_main(env).BASE_URL == expected
