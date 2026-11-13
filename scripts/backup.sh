#!/usr/bin/env sh
set -eu

# Linux 服务器每日备份：数据库 SQL + 后端附件卷；默认保留 30 天。
BACKUP_ROOT="${BACKUP_ROOT:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
STAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_ROOT"

docker compose exec -T mysql sh -c 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --events "$MYSQL_DATABASE"' > "$BACKUP_ROOT/database_$STAMP.sql"
docker compose exec -T backend tar -czf - -C /app uploads > "$BACKUP_ROOT/uploads_$STAMP.tar.gz"
find "$BACKUP_ROOT" -type f \( -name 'database_*.sql' -o -name 'uploads_*.tar.gz' \) -mtime +"$RETENTION_DAYS" -delete

echo "备份完成：$BACKUP_ROOT/database_$STAMP.sql"
