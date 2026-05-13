# ── Stage 1: run unit tests ────────────────────────────────────────────────
FROM python:3.12-slim AS test

WORKDIR /app

COPY common/ /common/
RUN pip install --no-cache-dir /common

COPY aggregation_service/pyproject.toml aggregation_service/poetry.lock* ./
RUN pip install --no-cache-dir poetry \
 && poetry config virtualenvs.create false \
 && poetry install --no-root --no-interaction --no-ansi

COPY aggregation_service/ /app/

RUN python -m pytest tests/ -x -q --tb=short


# ── Stage 2: production image ──────────────────────────────────────────────
FROM python:3.12-slim

# Forces Docker to complete the test stage before building this image
COPY --from=test /etc/os-release /tmp/.test-ok

WORKDIR /app

COPY common/ /common/
RUN pip install --no-cache-dir /common

COPY aggregation_service/pyproject.toml aggregation_service/poetry.lock* ./
RUN pip install --no-cache-dir poetry \
 && poetry config virtualenvs.create false \
 && poetry install --no-root --no-interaction --no-ansi --without dev

COPY aggregation_service/ /app/

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]