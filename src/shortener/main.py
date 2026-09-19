from fastapi import FastAPI, HTTPException
from hashids import Hashids
from pydantic import BaseModel, HttpUrl


class Link(BaseModel):
    url: HttpUrl
    ttl_m: int | None = 60


app = FastAPI()
hashids = Hashids(salt="url shortener", min_length=6)

links = {}

url_id = 0


@app.get("/{hash}")
def get_url_by_hash(hash: str):
    if not hash in links:
        raise HTTPException(status_code=404, detail="Item not found")

    return {"url": f"{links[hash]}"}


@app.post("/")
def post_shorter_url(link: Link):
    print(link.url)
    for hash, url in links.items():
        if url == link.url:
            return {"url": f"http://localhost:8000/{hash}"}

    global url_id
    url_id += 1
    url_hash = hashids.encode(url_id)

    links[url_hash] = link.url
    print(f"{links[url_hash]} -> https://locahost:8000/{url_hash}")

    return {"url": f"https://localhost:8000/{url_hash}"}
