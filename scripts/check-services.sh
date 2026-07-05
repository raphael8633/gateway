#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CADDYFILE="${SCRIPT_DIR}/../Caddyfile"

mapfile -t SERVICES < <(python3 - "$CADDYFILE" <<'PY'
import re
import sys
from pathlib import Path

src = Path(sys.argv[1]).read_text(encoding="utf-8")
handle_re = re.compile(r"^\s*handle(?:_path)?\s+(\S+?)\*?\s*\{", re.MULTILINE)
port_patterns = [
    re.compile(r"reverse_proxy\s+(?:localhost|127\.0\.0\.1):(\d+)"),
    re.compile(r"import\s+proxy_auth\s+(\d+)\b"),
    re.compile(r"import\s+proxy_auth_strip\s+\S+\s+(\d+)\b"),
]

for match in handle_re.finditer(src):
    path = match.group(1)
    if path == "/":
        continue
    depth = 1
    i = match.end()
    while i < len(src) and depth:
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
        i += 1
    body = src[match.end():i - 1]
    for pattern in port_patterns:
        found = pattern.search(body)
        if found:
            print(f"{found.group(1)} {path}")
            break
PY
)

PASS=0
FAIL=0

echo "=== Gateway Service Health Check ==="
echo ""

for service in "${SERVICES[@]}"; do
  port="${service%% *}"
  path="${service#* }"
  if ss -tlnp | grep -Eq "(127\\.0\\.0\\.1|localhost|\\*)[:.]${port}\\b|:${port}[[:space:]]"; then
    echo "PASS  ${path} (${port})"
    ((PASS += 1))
  else
    echo "FAIL  ${path} (${port})"
    ((FAIL += 1))
  fi
done

echo ""
echo "=== Results: ${PASS} PASS, ${FAIL} FAIL ==="

if (( FAIL > 0 )); then
  exit 1
fi
