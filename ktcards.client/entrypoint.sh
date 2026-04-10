#!/bin/sh
set -e

# Replace placeholder with the actual runtime value of VITE_GOOGLE_CLIENT_ID
find /usr/share/nginx/html -type f -name "*.js" | \
  xargs sed -i "s|__VITE_GOOGLE_CLIENT_ID__|${VITE_GOOGLE_CLIENT_ID}|g"

exec nginx -g "daemon off;"
