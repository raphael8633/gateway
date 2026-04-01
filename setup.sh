#!/usr/bin/env bash
set -euo pipefail

# ── Caddy Setup ───────────────────────────────────────────────────────────────
# Usage: bash setup.sh [--download-only]
# TLS:   Let's Encrypt HTTP-01 / TLS-ALPN-01 (no Cloudflare API needed)
# Req:   Port 80 or 443 open; raphtools.com A record pointing to this server

CADDY_DIR="$(cd "$(dirname "$0")" && pwd)"
DOWNLOAD_ONLY=false
[[ "${1:-}" == "--download-only" ]] && DOWNLOAD_ONLY=true

echo ""
echo "=== Caddy Setup ==="
echo ""

# ── 1. Download Caddy ─────────────────────────────────────────────────────────
echo "[1/3] Downloading Caddy..."
TMP_CADDY=$(mktemp)
curl -fsSL "https://caddyserver.com/api/download?os=linux&arch=amd64" -o "$TMP_CADDY"
chmod +x "$TMP_CADDY"
"$TMP_CADDY" version &>/dev/null || { echo "ERROR: binary broken" >&2; rm -f "$TMP_CADDY"; exit 1; }
echo "    ✓ $("$TMP_CADDY" version)"

# ── 2. Install binary (stop first to avoid 'text file busy') ─────────────────
echo "[2/3] Installing /usr/bin/caddy..."
sudo systemctl stop caddy 2>/dev/null || true
sudo cp "$TMP_CADDY" /usr/bin/caddy && sudo chmod +x /usr/bin/caddy
rm -f "$TMP_CADDY"
echo "    ✓ $(/usr/bin/caddy version)"

if [[ "$DOWNLOAD_ONLY" == true ]]; then
  echo ""; echo "=== Binary ready. Run 'bash setup.sh' to start. ==="; echo ""
  exit 0
fi

# ── 3. Validate, reload, restart ─────────────────────────────────────────────
echo "[3/3] Validating config and restarting Caddy..."
caddy validate --config "$CADDY_DIR/Caddyfile"
sudo systemctl daemon-reload
sudo systemctl restart caddy
sleep 2
sudo systemctl is-active --quiet caddy \
  && echo "    ✓ Caddy running" \
  || { echo "ERROR: Caddy failed. Run: sudo journalctl -u caddy -n 50" >&2; exit 1; }

echo ""
echo "=== Done ==="
echo "    https://raphtools.com  (TLS via Let's Encrypt, auto-renew)"
echo "    Monitor: sudo journalctl -u caddy -f"
echo ""
