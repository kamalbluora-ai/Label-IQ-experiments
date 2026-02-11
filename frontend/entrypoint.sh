#!/usr/bin/env sh
set -eu

# Default for local/dev if not set
: "${API_BASE:=http://localhost:8000/api}"

# dist/public is what your server serves as static
cat > /app/dist/public/config.js <<EOF
window.__CONFIG__ = { API_BASE: "${API_BASE}" };
EOF

exec node dist/index.cjs