#!/bin/bash
# Launch Chrome with remote debugging on port 9222, using a dedicated profile.
# Log into Domino once inside this window; the session is reused on later runs.
set -euo pipefail

PORT="${PORT:-9222}"
PROFILE_DIR="${PROFILE_DIR:-$HOME/chrome-debug-profile}"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

if [ ! -x "$CHROME" ]; then
    echo "Chrome not found at: $CHROME" >&2
    exit 1
fi

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port $PORT already in use; assuming Chrome is already running."
    exit 0
fi

mkdir -p "$PROFILE_DIR"
echo "Launching Chrome with --remote-debugging-port=$PORT, profile=$PROFILE_DIR"
exec "$CHROME" \
    --remote-debugging-port="$PORT" \
    --user-data-dir="$PROFILE_DIR"
