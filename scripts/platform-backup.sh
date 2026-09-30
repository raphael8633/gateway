#!/usr/bin/env bash
set -euo pipefail

PROJECTS_DIR=/home/ubuntu/projects
DATA_DIR=/home/ubuntu/data
BACKUP_ROOT="$DATA_DIR/backups"
TODAY="$(date +%F)"
DEST="$BACKUP_ROOT/$TODAY"
MIRROR="$BACKUP_ROOT/mirror"
# Large live DBs: one copy overwritten nightly (history lives off-site in restic,
# see raph-vps-state/offsite.sh) so 7 daily + 4 weekly dirs do not each hold ~0.7G.
LARGE="$BACKUP_ROOT/latest-large"
START_TS="$(date +%s)"

log() {
  printf '[%s] %s\n' "$(date -Is)" "$*"
}

backup_sqlite() {
  local src="$1" root="${2:-$DEST/sqlite}"
  local rel out
  rel="${src#/home/ubuntu/}"
  out="$root/${rel}.backup"
  mkdir -p "$(dirname "$out")"
  sqlite3 "$src" ".backup '$out'"
}

keep_recent_backups() {
  local -A keep=()
  local dirs=()
  local dir base weekly=0 count=0

  mapfile -t dirs < <(find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -regextype posix-extended -regex '.*/[0-9]{4}-[0-9]{2}-[0-9]{2}' -printf '%f\n' | sort -r)

  for base in "${dirs[@]}"; do
    if (( count < 7 )); then
      keep["$base"]=1
      ((count += 1))
    fi
    if [[ "$(date -d "$base" +%u)" == "7" && $weekly -lt 4 ]]; then
      keep["$base"]=1
      ((weekly += 1))
    fi
  done

  for base in "${dirs[@]}"; do
    if [[ -z "${keep[$base]:-}" ]]; then
      rm -rf "$BACKUP_ROOT/$base"
    fi
  done
}

main() {
  local sqlite_count=0
  local pg_count=0
  local config_count=0
  local mirror_count=0
  local large_count=0
  local secret_count=0

  rm -rf "$DEST/sqlite" "$DEST/postgres" "$DEST/config" "$LARGE"
  mkdir -p "$DEST"/{sqlite,postgres,config/systemd,config/env,config/global-auth,config/secrets} "$MIRROR" "$LARGE"

  log "backup start dest=$DEST"

  while IFS= read -r db; do
    backup_sqlite "$db"
    ((sqlite_count += 1))
  done < <(
    {
      find "$DATA_DIR" -path "$BACKUP_ROOT" -prune -o -type f \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' \) -print
      find "$PROJECTS_DIR/global-auth/data" -maxdepth 1 -type f -name 'db.sqlite3' -print 2>/dev/null
      find "$PROJECTS_DIR/vps2-vpn/data" -maxdepth 1 -type f -name '*.db' -print 2>/dev/null
      find "$PROJECTS_DIR/x-daily-digest/state" "$PROJECTS_DIR/raph-reader/backend/data" \
        "$PROJECTS_DIR/hermes/cron" -maxdepth 1 -type f -name '*.db' -size +0 -print 2>/dev/null
      find "$PROJECTS_DIR/hermes" -maxdepth 1 -type f -name '*.db' ! -name 'state.db' -size +0 -print
    } | sort -u
  )

  while IFS= read -r db; do
    backup_sqlite "$db" "$LARGE"
    ((large_count += 1))
  done < <(
    {
      find "$PROJECTS_DIR/hermes" -maxdepth 1 -type f -name 'state.db' -print
      find /home/ubuntu/.codex -maxdepth 1 -type f -name '*.sqlite' ! -name 'logs_*' -print
    } | sort -u
  )

  if sudo -u postgres pg_dump health_manage | gzip > "$DEST/postgres/health_manage.sql.gz"; then
    pg_count=1
  fi
  if sudo -u postgres pg_dumpall --globals-only | gzip > "$DEST/postgres/globals.sql.gz"; then
    ((pg_count += 1))
  fi

  rsync -a "$PROJECTS_DIR/global-auth/config/" "$DEST/config/global-auth/"
  config_count=$((config_count + 1))

  while IFS= read -r env_file; do
    local rel
    rel="${env_file#/home/ubuntu/}"
    mkdir -p "$DEST/config/env/$(dirname "$rel")"
    install -m 600 "$env_file" "$DEST/config/env/$rel"
    ((config_count += 1))
  done < <(
    {
      find "$DATA_DIR" -path "$BACKUP_ROOT" -prune -o -type f \( -name env -o -name '*.env' \) -print
      find "$PROJECTS_DIR/global-auth" -maxdepth 1 -type f -name '.env' -print
    } | sort -u
  )

  # Every regular unit file: package units are symlinks, so this is the custom set.
  find /etc/systemd/system -maxdepth 1 -type f -exec cp -a {} "$DEST/config/systemd/" \;
  mkdir -p "$DEST/config/systemd/user"
  find /home/ubuntu/.config/systemd/user -maxdepth 1 -type f -exec cp -a {} "$DEST/config/systemd/user/" \;
  config_count=$((config_count + 1))

  # Long-lived secrets for a rebuild (short-lived OAuth tokens are re-login, not backed up).
  # Only encrypted off-site copies leave this disk (restic); never add this dir to git.
  local secret
  for secret in /etc/wireguard /etc/outline-ss-server /etc/letsencrypt \
      /home/ubuntu/.ssh /home/ubuntu/.secrets /home/ubuntu/.config/headless /home/ubuntu/.xurl \
      /home/ubuntu/CLIProxyAPI/config.yaml /home/ubuntu/CLIProxyAPI/.local-key \
      /home/ubuntu/.cli-proxy-api /home/ubuntu/data/yt_cookies.txt; do
    [[ -e "$secret" ]] || continue
    mkdir -p "$DEST/config/secrets$(dirname "$secret")"
    cp -a "$secret" "$DEST/config/secrets$secret"
    ((secret_count += 1))
  done
  while IFS= read -r env_file; do
    mkdir -p "$DEST/config/secrets$(dirname "$env_file")"
    install -m 600 "$env_file" "$DEST/config/secrets$env_file"
    ((secret_count += 1))
  done < <(find "$PROJECTS_DIR" -maxdepth 4 \( -name node_modules -o -name .git -o -name tmp \) -prune -o \
             -type f \( -name '.env' -o -name '.env.local' -o -name '.envrc' \) -print)
  chmod -R go-rwx "$DEST/config/secrets"

  if [[ -d "$DATA_DIR/public-share" ]]; then
    rsync -a --delete "$DATA_DIR/public-share/" "$MIRROR/public-share/"
    mirror_count=$((mirror_count + 1))
  fi
  if [[ -d "$DATA_DIR/raph-reader/uploads" ]]; then
    rsync -a --delete "$DATA_DIR/raph-reader/uploads/" "$MIRROR/raph-reader-uploads/"
    mirror_count=$((mirror_count + 1))
  fi

  keep_recent_backups

  chown -R ubuntu:ubuntu "$BACKUP_ROOT"

  local elapsed size
  elapsed=$(( $(date +%s) - START_TS ))
  size="$(du -sh "$DEST" "$MIRROR" 2>/dev/null | awk '{total=total " " $1 ":" $2} END {gsub(/^ /, "", total); print total}')"
  log "backup OK sqlite=$sqlite_count large=$large_count postgres=$pg_count secrets=$secret_count config=$config_count mirrors=$mirror_count elapsed=${elapsed}s size=${size:-unknown}"
}

main "$@"
