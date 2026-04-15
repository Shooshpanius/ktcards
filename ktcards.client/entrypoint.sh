#!/bin/sh
set -e

# Replace Yandex.Metrika counter ID placeholder in index.html and *.js files at runtime.
# Set YANDEX_METRIKA_ID in docker-compose .env to activate the counter without
# storing the ID in the repository.
ESCAPED_YM_ID=$(printf '%s' "${YANDEX_METRIKA_ID:-0}" | sed 's/[|&\]/\\&/g')
sed -i "s|__YANDEX_METRIKA_ID__|${ESCAPED_YM_ID}|g" /usr/share/nginx/html/index.html
find /usr/share/nginx/html -name "*.js" \
  -exec sed -i "s|__YANDEX_METRIKA_ID__|${ESCAPED_YM_ID}|g" {} +

nginx -g 'daemon off;'
