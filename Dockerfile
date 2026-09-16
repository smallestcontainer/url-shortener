FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY --chown=nobody:nobody . .

USER nobody

CMD [ "fastapi", "run", "main.py"]