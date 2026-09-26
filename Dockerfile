FROM node:22-bookworm-slim@sha256:48e4b67d85f87bd551df43704e24d252f56cc5f8e9718841aace50f19948f0f9 AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim-bookworm@sha256:2325bb286ec344af3e5898cc224b5844e2707ac6e26b1632516fd3edc84a5e26
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app/backend
COPY backend/requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY --from=frontend /usr/local/bin/node /usr/local/bin/node
COPY --from=frontend /build/node_modules /app/frontend/node_modules
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN /app/frontend/node_modules/.bin/playwright install --with-deps chromium
RUN groupadd --gid 10001 docplatform && useradd --uid 10001 --gid 10001 --no-create-home docplatform     && mkdir -p /data/objects && chown -R docplatform:docplatform /data
COPY backend/ ./
COPY config.toml /app/config.toml
COPY --from=frontend /build/dist /app/frontend/dist
COPY scripts/ /app/scripts/
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "app.serve"]
