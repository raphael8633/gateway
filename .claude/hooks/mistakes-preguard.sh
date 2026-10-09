#!/usr/bin/env bash
# Installed by raph-power bin/raph-preguard-install. Runs the plugin repo's
# current preguard so fixes apply without reinstalling; fails open if missing.
target="/home/ubuntu/projects/raph-power/hooks/mistakes-preguard.sh"
[ -x "$target" ] || exit 0
exec "$target"
