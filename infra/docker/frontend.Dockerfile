# TEMP placeholder — frontend/ is empty until a separate session lands the
# real React app. Serves a static stub page so the `frontend` service and its
# port mapping can be validated today. Replace once real code exists with a
# proper multi-stage build (node build stage -> nginx serve stage), or switch
# to a dev-mode bind mount per infra/architecture.md.
FROM nginx:alpine

COPY docker/frontend-static/index.html /usr/share/nginx/html/index.html

EXPOSE 80
