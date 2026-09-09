# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 — build the Angular application bundle
# ---------------------------------------------------------------------------
FROM node:20-alpine AS build

WORKDIR /app

# NOTE: the build context is the repository ROOT (see deploy/docker-compose.yml), so every
# source path below is repo-relative — `frontend/...`, not `./...`.
# Dependencies first so the layer is cached while only sources change.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .

RUN npm run build -- --configuration production

# ---------------------------------------------------------------------------
# Stage 2 — serve the static bundle from nginx as an unprivileged user
# ---------------------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

# `outputPath` in angular.json is `dist/frontend`; the application builder emits
# the browser bundle into the `browser/` subdirectory.
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Run as the image's unprivileged `nginx` user (uid 101). A non-root process
# cannot bind port 80, so the server block listens on 8080 instead; nginx also
# needs write access to its cache, log and pid paths.
RUN mkdir -p /var/cache/nginx /var/run \
    && touch /var/run/nginx.pid \
    && chown -R nginx:nginx /var/cache/nginx /var/log/nginx /var/run/nginx.pid /usr/share/nginx/html \
    && chmod -R g+rwX /var/cache/nginx

USER nginx

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --spider --tries=1 http://127.0.0.1:8080/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
