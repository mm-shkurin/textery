# The published frontend, built and served from THIS directory.
#
# The monorepo already has an image (`infra/docker/frontend.Dockerfile`), but its build context is
# the repository root — it does `COPY frontend/ ./`, which cannot resolve in the repository the
# jury clones, where this directory IS the root. So that file is unreachable here, and a reviewer
# following the README had no standardized way to run anything. This Dockerfile takes its own
# directory as the context and depends on nothing above it.
#
# Multi-stage on purpose: the build needs Node, npm and 400 MB of devDependencies; serving needs a
# web server and 500 KB of static files. Shipping the builder would mean shipping a toolchain and
# a package manager into production for no runtime benefit.

FROM node:20-alpine AS build

WORKDIR /app

# The manifests first, and only them: this layer is cached until a dependency actually changes, so
# editing a component does not reinstall node_modules. `npm ci` rather than `npm install` — it
# installs exactly what the lockfile pins and fails if the two disagree, which is the difference
# between a reproducible image and one that quietly drifts.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# The build is also the type check (`tsc -b` runs first in this script) and the bundle-budget gate,
# so an image cannot be produced from code that would not pass CI.
RUN npm run build

FROM nginx:alpine AS serve

# The SPA itself.
COPY --from=build /app/dist /usr/share/nginx/html

# Served through a template, not a static conf: the API upstream differs per environment and a
# baked-in hostname would make the image environment-specific. nginx:alpine renders everything in
# /etc/nginx/templates through envsubst at container start.
COPY docker/nginx.conf.template /etc/nginx/templates/default.conf.template

# Where /api/ is forwarded. Overridden by compose or by `docker run -e`; the default names the
# service the monorepo's compose file publishes, so `docker compose up` in either place works.
ENV API_UPSTREAM=http://backend:8000

EXPOSE 80

# Fails the container rather than serving a blank page: if the SPA's entry document is not where
# nginx expects it, that is a broken build, and a container that reports healthy while returning
# 404 is worse than one that restarts.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --spider -q http://127.0.0.1/ || exit 1
