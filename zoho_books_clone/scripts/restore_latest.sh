#!/usr/bin/env bash
#
# restore_latest.sh — Restore the most recent database backup.
#
# Usage (from anywhere):
#   bash apps/zoho_books_clone/zoho_books_clone/scripts/restore_latest.sh [site] [-y]
#
#   [site]  optional site name (defaults to sites/currentsite.txt, else mysite.local)
#   -y      skip the confirmation prompt
#
# Pairs with scripts/clear_data.py, which takes a backup automatically before
# wiping. This restores that (or any latest) backup via `bench restore`.
#
# WARNING: this OVERWRITES the current database with the backup.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# scripts → package → app → apps → bench root
BENCH_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

# ── Resolve args ─────────────────────────────────────────────────────────────
SITE=""
ASSUME_YES=0
for arg in "$@"; do
  case "$arg" in
    -y|--yes) ASSUME_YES=1 ;;
    *)        SITE="$arg" ;;
  esac
done
if [ -z "$SITE" ]; then
  SITE="$(cat "$BENCH_ROOT/sites/currentsite.txt" 2>/dev/null || echo mysite.local)"
fi

BACKUP_DIR="$BENCH_ROOT/sites/$SITE/private/backups"
LATEST="$(ls -t "$BACKUP_DIR"/*-database.sql.gz 2>/dev/null | head -1 || true)"

if [ -z "$LATEST" ]; then
  echo "❌  No database backup found in: $BACKUP_DIR"
  exit 1
fi

echo "Site         : $SITE"
echo "Latest backup: $LATEST"
echo "⚠️   This will OVERWRITE the current database for '$SITE'."

if [ "$ASSUME_YES" -ne 1 ]; then
  read -r -p "Type 'yes' to restore: " CONFIRM
  [ "$CONFIRM" = "yes" ] || { echo "Aborted."; exit 1; }
fi

cd "$BENCH_ROOT"
echo "Restoring…"
bench --site "$SITE" restore "$LATEST" --force
echo "✅  Restored $SITE from $(basename "$LATEST")"
