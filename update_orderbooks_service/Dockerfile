# ── Stage 1: run unit tests ────────────────────────────────────────────────
FROM python:3.12-slim AS test

WORKDIR /update_orderbooks_service

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY common/ /common/
RUN pip install --no-cache-dir /common

COPY update_orderbooks_service/pyproject.toml update_orderbooks_service/poetry.lock* ./
RUN pip install --no-cache-dir poetry \
 && poetry config virtualenvs.create false \
 && poetry install --no-root --no-interaction --no-ansi

COPY update_orderbooks_service/ /update_orderbooks_service/

ENV PYTHONPATH=/update_orderbooks_service

RUN python -m pytest tests/ -x -q --tb=short


# ── Stage 2: production image ──────────────────────────────────────────────
FROM python:3.12-slim

COPY --from=test /etc/os-release /tmp/.test-ok

WORKDIR /update_orderbooks_service

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY common/ /common/
RUN pip install --no-cache-dir /common

COPY update_orderbooks_service/pyproject.toml update_orderbooks_service/poetry.lock* ./
RUN pip install --no-cache-dir poetry \
 && poetry config virtualenvs.create false \
 && poetry install --no-root --no-interaction --no-ansi --without dev

COPY update_orderbooks_service/ /update_orderbooks_service/

ENV PYTHONPATH=/update_orderbooks_service
ENV PYTHONUNBUFFERED=1

CMD ["tail", "-f", "/dev/null"]