# url-shortener

| Repository | Role | Relation to this repository |
|---|---|---|
| [url-shortener](https://github.com/smallestcontainer/url-shortener) | Application | This repository |
| [jenkins-gitops](https://github.com/smallestcontainer/jenkins-gitops) | CI | Jenkins server that runs this repository's `Jenkinsfile` on every push and pull request |
| [k3d-gitops](https://github.com/smallestcontainer/k3d-gitops) | CD | Kubernetes manifests that deploy this service to a k3d cluster |

A URL shortener built with [FastAPI](https://fastapi.tiangolo.com/) that stores links in
PostgreSQL. You register a long URL and get back a short link; opening the short link
redirects straight to the original URL.

## API

| Method and path | Request | Response |
|---|---|---|
| `POST /` | JSON `{"url": "<http(s) URL>"}` | `200` `{"url": "<BASE_URL>/<code>"}`; `422` if the URL is missing or not `http`/`https` |
| `GET /<code>` | | `302` redirect to the original URL; `404` if the code is unknown |

```bash
curl -X POST http://localhost:8000/ \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://example.com/some/long/page"}'
# {"url":"http://localhost:8000/OXzKpK"}

curl -i http://localhost:8000/OXzKpK
# HTTP/1.1 302 Found
# location: https://example.com/some/long/page
```

- Registering the same URL again returns the same short link.
- The request also accepts `ttl_m` (link lifetime in minutes), but it is not enforced yet:
  links never expire.
- Interactive API docs are served at `/docs`.

## How it works

Each URL is stored as a row in the `links` table. The short code is the row's `id`
encoded with [Hashids](https://hashids.org/) (`src/encoder.py`); codes are not stored, a
request for `GET /<code>` decodes the code back into the `id` and looks the row up.
Because codes derive from database ids, all replicas share one sequence and return the
same code for the same URL.

The table is created on startup if it does not exist. On PostgreSQL this runs under an
advisory lock, so replicas that start at the same time do not conflict. If two requests
store the same URL at once, the unique index on `url` rejects the second insert and the
existing link is returned.

### Repository structure

```
url-shortener/
├── src/
│   ├── main.py             # FastAPI app: routes, settings, database session
│   ├── db.py               # SQLAlchemy model of the links table and schema setup
│   └── encoder.py          # Hashids wrapper: row id <-> short code
├── tests/                  # pytest: API (test_api.py) and encoder (test_encoder.py)
├── Dockerfile              # Multi-stage image: base, tests (used by CI), run
├── Jenkinsfile             # CI/CD pipeline run by jenkins-gitops
├── requirements.txt        # Runtime dependencies
├── requirements-dev.txt    # Test dependencies
└── pytest.ini              # Test paths and options
```

### Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | yes | | SQLAlchemy URL of the database, e.g. `postgresql+psycopg://user:password@host:5432/db`. The app refuses to start without it |
| `BASE_URL` | no | `http://localhost:8000` | Public address of the service, used to build the short links it returns |

## Running locally

### With Docker

Start PostgreSQL and the application on a shared network. Data is kept in the
`shortener-pgdata` volume, so links survive container restarts.

```bash
docker network create shortener

docker run -d --name shortener-db --network shortener \
  -e POSTGRES_USER=shortener -e POSTGRES_PASSWORD=shortener -e POSTGRES_DB=shortener \
  -v shortener-pgdata:/var/lib/postgresql \
  postgres:18-alpine

docker build -t url-shortener .
docker run -d --name shortener --network shortener -p 8000:8000 --restart on-failure \
  -e DATABASE_URL=postgresql+psycopg://shortener:shortener@shortener-db:5432/shortener \
  url-shortener
```

`--restart on-failure` retries the start if PostgreSQL is not ready yet.
The service is available at http://localhost:8000.

To remove everything:

```bash
docker rm -f shortener shortener-db
docker volume rm shortener-pgdata
docker network rm shortener
```

### Tests

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

Tests use a temporary SQLite database and need no running PostgreSQL. To run the same
suite against PostgreSQL, point `TEST_DATABASE_URL` at a database whose tables can be
dropped:

```bash
TEST_DATABASE_URL=postgresql+psycopg://shortener:shortener@localhost:5432/shortener pytest
```

## CI/CD

[jenkins-gitops](https://github.com/smallestcontainer/jenkins-gitops) runs the
`Jenkinsfile` for every branch and pull request and reports the result as a GitHub check.

| Stage | Branches | What it does |
|---|---|---|
| Lint | all | `ruff format --check` and `ruff check`; findings are published as JUnit results and mark the build unstable without stopping it |
| Pytest | all | Builds the `tests` stage of the `Dockerfile` and runs `pytest` in it |
| Build | all | Builds the application image, tagged with the short commit hash |
| Image scan | all | Scans the image with [Trivy](https://trivy.dev/) for HIGH and CRITICAL vulnerabilities and publishes the report |
| publish | `master` | Pushes the image to Docker Hub |
| image tag bump | `master` | Sets the new tag in `kustomization.yaml` of [k3d-gitops](https://github.com/smallestcontainer/k3d-gitops); ArgoCD then rolls it out |

The pipeline expects from Jenkins the `DOCKERHUB_USERNAME` environment variable, the
`dockerhub` and `github-app` credentials, and access to the Docker socket (the Trivy
stage joins the host's `docker` group, GID `989`). All of these are provided by
jenkins-gitops.

## Deployment

The image runs as `nobody` and listens on port `8000`. The deployment must provide a
PostgreSQL database and set `DATABASE_URL`, plus `BASE_URL` set to the public address of
the service. Without `DATABASE_URL` the container exits on startup.
