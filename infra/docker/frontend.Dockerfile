# Real frontend image: multi-stage — build the Vite/React app, serve the
# static output via nginx. Build context is the repo root (see
# docker-compose.yml `frontend.build.context: ..`).
FROM node:20-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY infra/docker/nginx/frontend.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
