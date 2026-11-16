import os
from collections.abc import Iterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

import db
from encoder import Encoder


class LinkIn(BaseModel):
    url: HttpUrl
    ttl_m: int | None = 60


BASE_URL = (os.getenv("BASE_URL") or "http://localhost:8000").rstrip("/")
DATABASE_URL = os.getenv("DATABASE_URL")

encoder = Encoder(salt="url shortener", min_length=6)
SessionLocal = sessionmaker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set, e.g. postgresql+psycopg://user:password@host:5432/db"
        )

    engine = db.make_engine(DATABASE_URL)
    db.init_db(engine)
    SessionLocal.configure(bind=engine)
    yield
    engine.dispose()


app = FastAPI(lifespan=lifespan)


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def short_url(link_id: int) -> str:
    return f"{BASE_URL}/{encoder.encode(link_id)}"


def find_link_id(session: Session, url: str) -> int | None:
    return session.scalar(select(db.Link.id).where(db.Link.url == url))


@app.get("/{hash}")
def get_url_by_hash(hash: str, session: SessionDep):
    try:
        link_id = encoder.decode(hash)
    except ValueError:
        link_id = None

    link = session.get(db.Link, link_id) if link_id and link_id <= db.MAX_ID else None
    if link is None:
        raise HTTPException(status_code=404, detail="Item not found")

    return RedirectResponse(url=link.url, status_code=302)


@app.post("/")
def post_shorter_url(link: LinkIn, session: SessionDep):
    url = str(link.url)

    link_id = find_link_id(session, url)
    if link_id is None:
        new_link = db.Link(url=url)
        session.add(new_link)
        try:
            session.flush()
            link_id = new_link.id
            session.commit()
            print(f"{url} -> {short_url(link_id)}")
        except IntegrityError:
            session.rollback()
            link_id = find_link_id(session, url)

    return {"url": short_url(link_id)}
