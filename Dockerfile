# syntax=docker/dockerfile:1
# Local development image only. Production is deployed with rsync + supervisor (see .github/workflows/deploy.yml).

FROM oven/bun:1 AS bun

FROM python:3.14.5-slim-trixie AS dev

ARG UID=1000
ARG GID=1000

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_NO_SYNC=1 \
    PATH="/opt/venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
COPY --from=bun /usr/local/bin/bun /usr/local/bin/bun

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

COPY . .
RUN bun run tailwindcss -i ./static/css/input.css -o ./static/css/output.css --minify

# UID/GID must match the host user: start_app.py chmods the bind-mounted sources on every start.
RUN groupadd --gid "${GID}" app \
    && useradd --uid "${UID}" --gid "${GID}" --create-home --shell /bin/bash app \
    && mkdir -p /srv/log \
    && chown -R app:app /srv/app /srv/log /opt/venv

USER app

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD curl -fsS -H "Host: localhost" http://127.0.0.1:8000/health-check/app || exit 1

CMD ["python", "start_app.py", "--development"]
