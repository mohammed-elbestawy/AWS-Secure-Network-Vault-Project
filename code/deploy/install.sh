#!/usr/bin/env bash
# Installs the vault API on the private app instance (Amazon Linux 2023).
# Needs outbound HTTPS for pip and the RDS CA bundle, so run it while the NAT
# instance route exists. Run as root from the repository's code/ directory.
set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)"
APP=/opt/vault
REGION="${AWS_REGION:-eu-north-1}"

if [[ $EUID -ne 0 ]]; then
  echo "run as root: sudo bash deploy/install.sh" >&2
  exit 1
fi

dnf install -y python3 python3-pip

id -u vault >/dev/null 2>&1 || useradd --system --home-dir "$APP" --shell /sbin/nologin vault
mkdir -p "$APP"/{backend,frontend,certs} /var/log/vault
cp -r "$SRC"/backend/. "$APP/backend/"
cp -r "$SRC"/frontend/. "$APP/frontend/"

python3 -m venv "$APP/venv"
"$APP/venv/bin/pip" install --quiet --upgrade pip
"$APP/venv/bin/pip" install --quiet -r "$APP/backend/requirements.txt"

curl -fsSL https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem \
  -o "$APP/certs/rds-global-bundle.pem"

cat > /etc/vault.env <<ENV
STORE=mysql
AWS_REGION=$REGION
VAULT_SSM_PREFIX=/vault/db
DB_SSL_CA=$APP/certs/rds-global-bundle.pem
LOG_FILE=/var/log/vault/app.log
VAULT_FRONTEND_DIR=$APP/frontend
ENV
chmod 640 /etc/vault.env
chown root:vault /etc/vault.env

chown -R vault:vault /var/log/vault
chown -R root:vault "$APP"
chmod -R g+rX,o-rwx "$APP"

install -m 644 "$SRC"/deploy/vault.service /etc/systemd/system/vault.service
install -m 644 "$SRC"/deploy/vault-purge.service /etc/systemd/system/vault-purge.service
install -m 644 "$SRC"/deploy/vault-purge.timer /etc/systemd/system/vault-purge.timer

# The lab web server from Step 8 listens on port 80 too.
systemctl disable --now web 2>/dev/null || true

systemctl daemon-reload
systemctl enable --now vault.service vault-purge.timer

sleep 3
curl -fsS http://localhost/healthz && echo
curl -fsS http://localhost/api/health && echo
echo "vault is running"
