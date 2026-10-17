#!/usr/bin/env bash
# WireGuard gateway in the public subnet of VPC A (Amazon Linux 2023).
# Also required in the console: disable Source/destination check on the instance.
set -euo pipefail

TUNNEL_NET="10.200.0.0/24"
SERVER_ADDR="10.200.0.1/24"
PORT=51820

if [[ $EUID -ne 0 ]]; then
  echo "run as root" >&2
  exit 1
fi

dnf install -y wireguard-tools iptables-nft

umask 077
mkdir -p /etc/wireguard
if [[ ! -f /etc/wireguard/server.key ]]; then
  wg genkey | tee /etc/wireguard/server.key | wg pubkey > /etc/wireguard/server.pub
fi

echo 'net.ipv4.ip_forward = 1' > /etc/sysctl.d/90-wireguard.conf
sysctl --system >/dev/null

IFACE=$(ip -o -4 route show to default | awk '{print $5}' | head -1)

cat > /etc/wireguard/wg0.conf <<CONF
[Interface]
Address = ${SERVER_ADDR}
ListenPort = ${PORT}
PrivateKey = $(cat /etc/wireguard/server.key)
PostUp = iptables -t nat -A POSTROUTING -s ${TUNNEL_NET} -o ${IFACE} -j MASQUERADE; iptables -A FORWARD -i wg0 -j ACCEPT; iptables -A FORWARD -o wg0 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
PostDown = iptables -t nat -D POSTROUTING -s ${TUNNEL_NET} -o ${IFACE} -j MASQUERADE; iptables -D FORWARD -i wg0 -j ACCEPT; iptables -D FORWARD -o wg0 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
CONF

systemctl enable --now wg-quick@wg0
echo
echo "Server public key (give this to the peer):"
cat /etc/wireguard/server.pub
