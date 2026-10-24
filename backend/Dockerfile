# One image, three entrypoints: backend (API), worker (job runner), migrate (one-shot). SRS §4.4, §26.
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv PATH="/opt/venv/bin:$PATH"
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY alembic.ini ./
COPY alembic ./alembic
COPY mulenetx ./mulenetx
RUN uv sync --frozen --no-dev
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh \
    && useradd --create-home --uid 10001 mulenetx \
    && mkdir -p /data/artifacts /data/staging && chown -R mulenetx:mulenetx /data
USER mulenetx
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["backend"]
