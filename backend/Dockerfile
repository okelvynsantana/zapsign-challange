# syntax=docker/dockerfile:1
#
# Backend image — Django 5 + DRF served by gunicorn.
#
# Multi-stage, non-root, Kubernetes-ready.
# IMPORTANT: the build context is the REPOSITORY ROOT (see deploy/docker-compose.yml and
# .github/workflows/images.yml), so every COPY path below is prefixed with `backend/`.
#
#   docker build -f backend/Dockerfile -t zapsign-backend:local .

# ---------------------------------------------------------------------------
# Stage 1 — builder: compile wheels into a self-contained virtualenv
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Build toolchain for any dependency that still ships an sdist.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# --- dependency layer -------------------------------------------------------
# Copy only the manifest first so that changing application source does not
# invalidate the (slow) dependency install layer.
COPY backend/pyproject.toml /app/pyproject.toml

# Resolve the *runtime* dependency list from pyproject.toml (PEP 621). The `dev`
# optional-dependency group is deliberately NOT installed in the image.
RUN python -c "import tomllib, pathlib; \
proj = tomllib.loads(pathlib.Path('/app/pyproject.toml').read_text(encoding='utf-8')); \
deps = proj.get('project', {}).get('dependencies', []); \
pathlib.Path('/tmp/requirements.txt').write_text('\n'.join(deps) + '\n', encoding='utf-8')"

# gunicorn is the production WSGI server; installed explicitly so the image works
# whether or not it is declared in pyproject.toml runtime dependencies.
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir gunicorn

# --- application layer ------------------------------------------------------
COPY backend/ /app/

# Install the project itself (console scripts / package metadata) without
# re-resolving dependencies — they are already pinned into the venv above.
RUN pip install --no-cache-dir --no-deps .

# ---------------------------------------------------------------------------
# Stage 2 — runtime: slim, non-root, no build toolchain
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.prod

# ca-certificates: outbound TLS to ZapSign / OpenAI.
# curl: used by HEALTHCHECK here and by the Compose healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user with a high, stable uid (Kubernetes runAsUser / runAsNonRoot).
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin app

COPY --from=builder --chown=10001:10001 /opt/venv /opt/venv

WORKDIR /app
COPY --from=builder --chown=10001:10001 /app /app

# Writable location for collected static files, if prod settings enable WhiteNoise.
RUN mkdir -p /app/staticfiles && chown -R 10001:10001 /app/staticfiles

USER 10001:10001

EXPOSE 8000

# `/api/health/` is unauthenticated by design (infra probes must not need app credentials).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/health/ || exit 1

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
