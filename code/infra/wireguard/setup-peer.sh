#!/usr/bin/env bash
# Simulated on-premises peer (eu-west-1).
# Usage: sudo bash setup-peer.sh <server_public_key> <server_public_ip>
set -euo pipefail

SERVER_KEY="${1:?server public key required}"
SERVER_IP="${2:?server public IP required}"
PORT=51820

if [[ $EUID -ne 0 ]]; then
  echo "run as root" >&2
  exit 1
fi

dnf install -y wireguard-tools

umask 077
mkdir -p /etc/wireguard
if [[ ! -f /etc/wireguard/peer.key ]]; then
  wg genkey | tee /etc/wireguard/peer.key | wg pubkey > /etc/wireguard/peer.pub
fi

cat > /etc/wireguard/wg0.conf <<CONF
[Interface]
Address = 10.200.0.2/24
ListenPort = ${PORT}
PrivateKey = $(cat /etc/wireguard/peer.key)

[Peer]
PublicKey = ${SERVER_KEY}
Endpoint = ${SERVER_IP}:${PORT}
AllowedIPs = 10.200.0.0/24, 10.0.0.0/16
PersistentKeepalive = 25
CONF

systemctl enable --now wg-quick@wg0
echo
echo "Peer public key (add it on the server with add-peer.sh):"
cat /etc/wireguard/peer.pub
