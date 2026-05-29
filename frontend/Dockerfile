# Frontend: Vite static build + nginx /api proxy to backend
# Build from repo root: docker build -f frontend/Dockerfile -t IMAGE .
FROM node:20-alpine AS builder

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ ./
RUN npm run build:docker

FROM nginx:alpine

RUN apk add --no-cache gettext

COPY --from=builder /build/dist /usr/share/nginx/html/app
COPY frontend/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY frontend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PORT=8080
EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]
