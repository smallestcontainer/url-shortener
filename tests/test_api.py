import importlib
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

import db
import main

# Tests run against a throwaway SQLite file by default. Set TEST_DATABASE_URL to
# run the same suite against PostgreSQL; its tables are dropped between tests.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@pytest.fixture
def database_url(tmp_path):
    return TEST_DATABASE_URL or f"sqlite:///{tmp_path / 'links.db'}"


@pytest.fixture
def engine(database_url):
    engine = db.make_engine(database_url)
    db.Base.metadata.drop_all(engine)
    db.init_db(engine)
    yield engine
    db.Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(engine, monkeypatch):
    monkeypatch.setattr(main, "BASE_URL", "http://test")
    session_factory = sessionmaker(bind=engine)

    def get_test_session():
        with session_factory() as session:
            yield session

    main.app.dependency_overrides[main.get_session] = get_test_session
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


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


def test_post_long_url(client):
    url = "https://example.com/" + "a" * 2000
    short = shorten(client, url)
    response = client.get(f"/{hash_of(short)}", follow_redirects=False)
    assert response.headers["location"] == url


def test_post_concurrent_insert_returns_existing_link(client, engine, monkeypatch):
    # Simulate another replica inserting the same URL between our SELECT and INSERT.
    url = "https://example.com/race"
    with sessionmaker(bind=engine)() as session:
        session.add(db.Link(url=url))
        session.commit()

    real_find = main.find_link_id
    calls = []

    def find_missing_first_time(session, url):
        calls.append(url)
        return None if len(calls) == 1 else real_find(session, url)

    monkeypatch.setattr(main, "find_link_id", find_missing_first_time)

    assert shorten(client, url) == f"http://test/{main.encoder.encode(1)}"
    assert len(calls) == 2


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


@pytest.mark.parametrize(
    "code",
    [
        pytest.param("unknown", id="invalid-code"),
        pytest.param(main.encoder.encode(999), id="valid-code-missing-row"),
        pytest.param(main.encoder.encode(0), id="zero-id"),
        pytest.param(main.encoder.encode(db.MAX_ID + 1), id="id-beyond-bigint"),
    ],
)
def test_get_unknown_hash_returns_404(client, code):
    response = client.get(f"/{code}", follow_redirects=False)
    assert response.status_code == 404


def test_links_survive_restart(database_url, engine, monkeypatch):
    # Two app lifespans over the same database stand in for a container restart.
    monkeypatch.setattr(main, "DATABASE_URL", database_url)

    with TestClient(main.app) as client:
        short = shorten(client, "https://example.com/persistent")

    with TestClient(main.app) as client:
        response = client.get(f"/{hash_of(short)}", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "https://example.com/persistent"
        assert shorten(client, "https://example.com/persistent") == short


def test_startup_fails_without_database_url(monkeypatch):
    monkeypatch.setattr(main, "DATABASE_URL", None)
    with pytest.raises(RuntimeError, match="DATABASE_URL"), TestClient(main.app):
        pass


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
