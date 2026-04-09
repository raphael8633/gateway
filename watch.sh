#!/bin/bash
# watch.sh — auto-sync on file changes
#
# README.md 變更 → gen-index.py → www/index.html 自動更新
# Caddyfile 變更 → caddy reload
#
# 需求: inotify-tools (apt install inotify-tools)
# 用法: ./watch.sh            (前景執行)
#       nohup ./watch.sh &    (背景執行)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
README="$(realpath "$SCRIPT_DIR/../README.md")"
CADDYFILE="$SCRIPT_DIR/Caddyfile"

if ! command -v inotifywait &>/dev/null; then
  echo "Error: inotifywait not found. Install with: apt install inotify-tools" >&2
  exit 1
fi

echo "[watch] Started. Watching:"
echo "  $README"
echo "  $CADDYFILE"

inotifywait -m -e close_write --format '%w' "$README" "$CADDYFILE" 2>/dev/null \
| while IFS= read -r changed; do
    if [[ "$changed" == "$README" ]]; then
      echo "[watch] README.md changed → regenerating index.html"
      python3 "$SCRIPT_DIR/gen-index.py" && echo "[watch] Done."
    elif [[ "$changed" == "$CADDYFILE" ]]; then
      echo "[watch] Caddyfile changed → caddy reload"
      caddy reload --config "$CADDYFILE" && echo "[watch] Done."
    fi
done
