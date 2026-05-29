#!/usr/bin/env bash
set -euo pipefail

: "${MYSQL_HOST:=127.0.0.1}"
: "${MYSQL_PORT:=3306}"
: "${MYSQL_DATABASE:=audio_analysis}"
: "${MYSQL_USER:=audio_user}"
: "${BACKUP_DIR:=./backups}"

mkdir -p "${BACKUP_DIR}"
timestamp="$(date +%Y%m%d_%H%M%S)"
out="${BACKUP_DIR}/${MYSQL_DATABASE}_${timestamp}.sql.gz"

mysqldump \
  --single-transaction \
  --routines \
  --triggers \
  --host="${MYSQL_HOST}" \
  --port="${MYSQL_PORT}" \
  --user="${MYSQL_USER}" \
  --password="${MYSQL_PASSWORD:?MYSQL_PASSWORD is required}" \
  "${MYSQL_DATABASE}" | gzip > "${out}"

echo "backup written to ${out}"
