#!/bin/sh
set -e

# Start Caddy in the background using the original PORT environment variable.
caddy start --config /app/Caddyfile --adapter caddyfile

# Override HOST and PORT for the Python/Waitress backend.
# This ensures Waitress only listens on the local interface and does not clash with Caddy's port.
export HOST=127.0.0.1
export PORT=9099

# Run python app.py using exec to replace the shell, allowing tini to correctly forward signals.
exec python app.py
