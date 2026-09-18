FROM python:3.14-alpine AS base 

WORKDIR /app

COPY pyproject.toml ./

COPY src/ src/


FROM base AS tests

RUN pip install -e ".[dev]" --no-cache-dir

COPY tests/ tests/


FROM base AS run

RUN pip install --no-cache-dir .

COPY --chown=nobody:nobody src/ src/

USER nobody

CMD [ "fastapi", "run", "main.py"]