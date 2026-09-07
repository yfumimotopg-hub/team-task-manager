# syntax=docker/dockerfile:1

# Development image for the backend.
# Python: canonical `python:` image, 3.14 slim-bookworm variant (patch floats within 3.14).
# uv: copied from Astral's official image, pinned to an explicit version (not :latest).
FROM python:3.14-slim-bookworm

# Runtime lib needed by the Node.js binary that the pyright PyPI wrapper
# fetches via nodeenv; python:*-slim omits it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 \
    && rm -rf /var/lib/apt/lists/*

# uv 0.12.10
COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /usr/local/bin/

# Keep the project virtualenv out of the bind-mounted source tree so the host never
# gets a .venv and Linux-native wheels stay inside the container only.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_CACHE_DIR=/cache/uv \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app
