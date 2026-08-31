#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT="${1:-/tmp/openfortivpn-gui-render.png}"
shift || true

if command -v xvfb-run >/dev/null 2>&1; then
    exec xvfb-run -a python3 "$REPO_DIR/dev/render_smoke.py" "$OUTPUT" "$@"
fi

DISPLAY_NUM=99
while [ -e "/tmp/.X${DISPLAY_NUM}-lock" ]; do
    DISPLAY_NUM=$((DISPLAY_NUM + 1))
done

Xvfb ":${DISPLAY_NUM}" -screen 0 1024x768x24 &
XVFB_PID=$!
trap 'kill "$XVFB_PID" 2>/dev/null || true' EXIT

# espera o Xvfb subir antes de tentar conectar
for _ in $(seq 1 20); do
    if [ -e "/tmp/.X11-unix/X${DISPLAY_NUM}" ]; then
        break
    fi
    sleep 0.1
done

DISPLAY=":${DISPLAY_NUM}" python3 "$REPO_DIR/dev/render_smoke.py" "$OUTPUT" "$@"
