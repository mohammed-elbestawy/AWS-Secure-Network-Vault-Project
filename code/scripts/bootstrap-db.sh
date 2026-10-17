#!/usr/bin/env bash
# Creates the schema and a least-privilege application user.
# Run once from the app instance. Usage: bash bootstrap-db.sh <rds_endpoint>
# The master password is in Secrets Manager (secret created by RDS).
set -euo pipefail

DB_HOST="${1:?RDS endpoint required}"
APP_PW="$(openssl rand -base64 36 | tr -dc 'A-Za-z0-9' | cut -c1-28)"
SCHEMA="$(cd "$(dirname "$0")/.." && pwd)/backend/schema.sql"

read -r -s -p "RDS master password: " MASTER_PW
echo

export MYSQL_PWD="$MASTER_PW"
mysql -h "$DB_HOST" -u admin --ssl appdb < "$SCHEMA"
mysql -h "$DB_HOST" -u admin --ssl appdb <<SQL
CREATE USER IF NOT EXISTS 'vault_app'@'%' IDENTIFIED BY '${APP_PW}' REQUIRE SSL;
ALTER USER 'vault_app'@'%' IDENTIFIED BY '${APP_PW}' REQUIRE SSL;
GRANT SELECT, INSERT, UPDATE, DELETE ON appdb.secrets TO 'vault_app'@'%';
FLUSH PRIVILEGES;
SQL
unset MYSQL_PWD

echo
echo "Schema created and user 'vault_app' configured."
echo "Store these in Parameter Store (shown once):"
echo "  /vault/db/host     = $DB_HOST"
echo "  /vault/db/name     = appdb"
echo "  /vault/db/user     = vault_app"
echo "  /vault/db/password = $APP_PW   (SecureString)"
