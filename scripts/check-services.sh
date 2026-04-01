#!/usr/bin/env bash
# Health-check script for gateway services
# Checks each expected port is listening

PORTS=(3001 4173 8000 8501 8502)
LABELS=(
  "polymarket-address-tracker (3001)"
  "maple-toolkit-frontend (4173)"
  "maple-toolkit-api (8000)"
  "polymarket-simulation (8501)"
  "polymarket-nothing-happens (8502)"
)

PASS=0
FAIL=0

echo "=== Gateway Service Health Check ==="
echo ""

for i in "${!PORTS[@]}"; do
  port="${PORTS[$i]}"
  label="${LABELS[$i]}"
  if ss -tlnp | grep -q ":${port} "; then
    echo "PASS  ${label}"
    ((PASS++))
  else
    echo "FAIL  ${label}"
    ((FAIL++))
  fi
done

echo ""
echo "=== Results: ${PASS} PASS, ${FAIL} FAIL ==="

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
