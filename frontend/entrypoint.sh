#!/bin/sh
set -eu

: "${API_UPSTREAM_HOST:?API_UPSTREAM_HOST is required (host:port or Cloud Run host, no scheme)}"
: "${PORT:=8080}"
: "${API_UPSTREAM_SCHEME:=https}"

export PORT API_UPSTREAM_HOST API_UPSTREAM_SCHEME

# Strip scheme if passed by mistake
API_UPSTREAM_HOST="${API_UPSTREAM_HOST#https://}"
API_UPSTREAM_HOST="${API_UPSTREAM_HOST#http://}"
export API_UPSTREAM_HOST

case "$API_UPSTREAM_SCHEME" in
  http|https) ;;
  *) echo "API_UPSTREAM_SCHEME must be http or https" >&2; exit 1 ;;
esac

envsubst '${PORT} ${API_UPSTREAM_HOST} ${API_UPSTREAM_SCHEME}' \
  < /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf

exec nginx -g 'daemon off;'
