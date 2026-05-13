# ── Stage 1: run unit tests ────────────────────────────────────────────────
FROM python:3.12-slim AS test

WORKDIR /app

COPY pyproject.toml poetry.lock* ./
RUN pip install --no-cache-dir poetry \
 && poetry config virtualenvs.create false \
 && poetry install --no-root --no-interaction --no-ansi

COPY . /app/

RUN python -m pytest tests/ -x -q --tb=short


# ── Stage 2: production image ──────────────────────────────────────────────
FROM python:3.12-slim

COPY --from=test /etc/os-release /tmp/.test-ok

WORKDIR /app

COPY pyproject.toml poetry.lock* ./
RUN pip install --no-cache-dir poetry \
 && poetry config virtualenvs.create false \
 && poetry install --no-root --no-interaction --no-ansi --without dev

COPY . /app/

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]