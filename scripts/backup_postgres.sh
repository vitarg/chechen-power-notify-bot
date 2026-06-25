#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/chechen-power-notify/backups}"
DATABASE_URL="${DATABASE_URL:-postgresql://chechen_power:change-me@127.0.0.1:5432/chechen_power}"

mkdir -p "$BACKUP_DIR"
timestamp="$(date +%Y%m%d-%H%M%S)"
pg_dump "$DATABASE_URL" | gzip > "$BACKUP_DIR/chechen_power-$timestamp.sql.gz"
find "$BACKUP_DIR" -type f -name 'chechen_power-*.sql.gz' -mtime +7 -delete

