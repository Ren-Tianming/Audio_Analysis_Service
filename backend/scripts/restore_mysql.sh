#!/usr/bin/env bash
set -euo pipefail

: "${MYSQL_HOST:=127.0.0.1}"
: "${MYSQL_PORT:=3306}"
: "${MYSQL_DATABASE:=audio_analysis}"
: "${MYSQL_USER:=audio_user}"

backup_file="${1:?usage: restore_mysql.sh <backup.sql.gz|backup.sql>}"

if [[ "${backup_file}" == *.gz ]]; then
  gzip -dc "${backup_file}" | mysql \
    --host="${MYSQL_HOST}" \
    --port="${MYSQL_PORT}" \
    --user="${MYSQL_USER}" \
    --password="${MYSQL_PASSWORD:?MYSQL_PASSWORD is required}" \
    "${MYSQL_DATABASE}"
else
  mysql \
    --host="${MYSQL_HOST}" \
    --port="${MYSQL_PORT}" \
    --user="${MYSQL_USER}" \
    --password="${MYSQL_PASSWORD:?MYSQL_PASSWORD is required}" \
    "${MYSQL_DATABASE}" < "${backup_file}"
fi

echo "restore completed from ${backup_file}"
