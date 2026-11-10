import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl

from encoder import Encoder


class Link(BaseModel):
    url: HttpUrl
    ttl_m: int | None = 60


app = FastAPI()
encoder = Encoder(salt="url shortener", min_length=6)

BASE_URL = (os.getenv("BASE_URL") or "http://localhost:8000").rstrip("/")

links = {}

url_id = 0


@app.get("/{hash}")
def get_url_by_hash(hash: str):
    if hash not in links:
        raise HTTPException(status_code=404, detail="Item not found")

    return RedirectResponse(url=str(links[hash]), status_code=302)


@app.post("/")
def post_shorter_url(link: Link):
    print(link.url)
    for hash, url in links.items():
        if url == link.url:
            return {"url": f"{BASE_URL}/{hash}"}

    global url_id
    url_id += 1
    url_hash = encoder.encode(url_id)

    links[url_hash] = link.url
    print(f"{links[url_hash]} -> {BASE_URL}/{url_hash}")

    return {"url": f"{BASE_URL}/{url_hash}"}
