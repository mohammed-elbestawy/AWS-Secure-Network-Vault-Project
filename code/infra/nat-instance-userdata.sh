#!/bin/bash
# User data for the NAT instance (Amazon Linux 2023, public subnet).
# Also required in the console: disable Source/destination check on the instance.
set -eux
dnf install -y iptables-services
systemctl enable --now iptables

echo 'net.ipv4.ip_forward = 1' > /etc/sysctl.d/90-nat.conf
sysctl --system

IFACE=$(ip -o -4 route show to default | awk '{print $5}' | head -1)
iptables -t nat -A POSTROUTING -o "$IFACE" -s 10.0.0.0/16 -j MASQUERADE
iptables -F FORWARD
service iptables save
