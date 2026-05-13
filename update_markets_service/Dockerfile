FROM python:3.12-slim

WORKDIR /update_markets_service

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY common/ /common/
RUN pip install --no-cache-dir /common

COPY update_markets_service/pyproject.toml update_markets_service/poetry.lock* ./
RUN pip install --no-cache-dir poetry \
 && poetry config virtualenvs.create false \
 && poetry install --no-root --no-interaction --no-ansi --without dev

COPY update_markets_service/ /update_markets_service/

ENV PYTHONPATH=/update_markets_service
ENV PYTHONUNBUFFERED=1

CMD ["tail", "-f", "/dev/null"]