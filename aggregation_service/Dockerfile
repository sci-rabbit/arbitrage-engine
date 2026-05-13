FROM python:3.12-slim

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