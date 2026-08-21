#!/bin/bash
set -e
cd /opt/su-portal
export PGPASSWORD=$(grep '^DB_PASSWORD=' .env | cut -d= -f2-)
pg_dump -h 127.0.0.1 -U suportal suportal | gzip > /backup/portal/suportal-$(date +%F).sql.gz
find /backup/portal -name 'suportal-*.sql.gz' -mtime +30 -delete
