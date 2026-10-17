#!/usr/bin/env bash
# Usage: sudo bash add-peer.sh <peer_public_key> [peer_tunnel_ip]
set -euo pipefail

PEER_KEY="${1:?peer public key required}"
PEER_IP="${2:-10.200.0.2}"

if ! grep -q "$PEER_KEY" /etc/wireguard/wg0.conf; then
  cat >> /etc/wireguard/wg0.conf <<CONF

[Peer]
PublicKey = ${PEER_KEY}
AllowedIPs = ${PEER_IP}/32
CONF
fi

wg syncconf wg0 <(wg-quick strip wg0)
wg show wg0
