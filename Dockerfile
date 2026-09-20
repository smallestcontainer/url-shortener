FROM python:3.14-alpine AS base 

WORKDIR /app

COPY requirements.txt .

COPY pyproject.toml .

RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/


FROM base AS tests

COPY requirements-dev.txt .

RUN pip install --no-cache-dir -r requirements-dev.txt

COPY tests/ tests/


FROM base AS run

RUN chown nobody:nobody src 

USER nobody

CMD [ "fastapi", "run", "src/main.py"]