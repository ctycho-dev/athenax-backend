FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY alembic.ini logger_config.yaml start.sh ./
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts

RUN python -m pip install --upgrade pip && pip install -e .
RUN chmod +x /app/start.sh

EXPOSE 8844

CMD ["sh", "./start.sh"]