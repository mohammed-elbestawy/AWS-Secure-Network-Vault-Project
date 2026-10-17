# Network Plan

The subnet and CIDR plan, route tables, security rule matrix and the connectivity tests. Names can differ in your account (`prod-vpc` instead of `sn-vpc`); identify a resource by its CIDR.

## CIDR plan

| Network | CIDR | Purpose |
|---|---|---|
| VPC A `sn-vpc` | `10.0.0.0/16` | The main application network |
| VPC B `sn-vpc-b` | `10.1.0.0/16` | Shared services, reached through Transit Gateway and PrivateLink |
| On-premises (simulated) `sn-onprem`, `eu-west-1` | `192.168.0.0/16` | Stand-in for an office |
| WireGuard tunnel | `10.200.0.0/24` | Gateway `.1`, peer `.2` |

CIDRs do not overlap, which is what makes peering and Transit Gateway routing possible.

| Subnet | CIDR | AZ | Tier |
|---|---|---|---|
| public 1 | `10.0.0.0/20` | `eu-north-1a` | ALB, NAT instance, WireGuard gateway |
| public 2 | `10.0.16.0/20` | `eu-north-1b` | ALB |
| app 1 | `10.0.128.0/20` | `eu-north-1a` | Flask server, endpoints, TGW attachment, monitor |
| app 2 | `10.0.144.0/20` | `eu-north-1b` | Spare capacity |
| data 1 | `10.0.32.0/24` | `eu-north-1a` | RDS |
| data 2 | `10.0.33.0/24` | `eu-north-1b` | RDS subnet group |
| VPC B private | `10.1.10.0/24` | `eu-north-1a` | Shared services instance, NLB |
| on-prem public | `192.168.1.0/24` | `eu-west-1a` | WireGuard peer |

## Route tables

| Route table | Destination | Target | Note |
|---|---|---|---|
| Public (wizard) | `10.0.0.0/16` | local | |
| | `0.0.0.0/0` | Internet gateway | |
| App (wizard) | `10.0.0.0/16` | local | |
| | S3 prefix list | S3 gateway endpoint | Added by the wizard |
| | `0.0.0.0/0` | NAT instance | **Temporary.** Removed before Flow Logs |
| | `10.1.0.0/16` | Transit Gateway | Added in the TGW stage |
| Data `sn-rt-data` | `10.0.0.0/16` | local | Nothing else: no path to the internet |
| VPC B main | `10.1.0.0/16` | local | |
| | `10.0.0.0/16` | Transit Gateway | |
| On-prem | `192.168.0.0/16` | local | |
| | `0.0.0.0/0` | Internet gateway | Needed for the WireGuard endpoint |
| Transit Gateway (default) | `10.0.0.0/16`, `10.1.0.0/16` | attachments | Propagated |

The WireGuard gateway masquerades `10.200.0.0/24`, so VPC A needs no route for the tunnel network.

## Security matrix

**Security groups** (stateful, attached to the interface)

| Group | Inbound | Outbound |
|---|---|---|
| `sn-alb-sg` | HTTP from anywhere | HTTP to `sn-app-sg` |
| `sn-app-sg` | HTTP from `sn-alb-sg`, from `sn-wg-sg` | HTTPS to `10.0.0.0/16` and the S3 prefix list, MySQL to `sn-db-sg`, HTTP to `10.0.0.0/16`, HTTP and ICMP to `10.1.0.0/16` |
| `sn-db-sg` | MySQL from `sn-app-sg` | none |
| `sn-vpce-sg` | HTTPS from `10.0.0.0/16` | default |
| `sn-wg-sg` | UDP 51820 from the on-prem Elastic IP only | default |
| `sn-monitor-sg` | UDP 4789 from `10.0.0.0/16` | HTTPS to the VPC and S3 only |
| `sn-isolation-sg` | none | none |

**Network ACLs** (stateless, attached to the subnet)

| ACL | Subnets | Allows in | Allows out |
|---|---|---|---|
| `sn-nacl-public` | public | 80, 443, ephemeral; UDP 51820 from the on-prem IP | ephemeral, 80 to app, 443, 80; UDP 51820 to the on-prem IP |
| `sn-nacl-app` | app | 80 from public, ephemeral; 80 and ICMP from `10.1.0.0/16` and from its own CIDR (TGW attachment) | ephemeral, 443, 3306 to data; 80 and ICMP to `10.1.0.0/16` |
| `sn-nacl-data` | data | 3306 from app | ephemeral to app |

Anything that places an interface in a subnet (Transit Gateway attachment, interface endpoint, load balancer) is filtered by that subnet's ACL. That caused the hardest fault in this build.

## Connectivity tests

All tests use `curl -m 5 -sS URL; echo "exit=$?"` so a failure is visible. `0` ok, `28` timeout, `7` no route or reject, `6` DNS.

| Test | From → to | Expected | Evidence |
|---|---|---|---|
| Private server has no public IP | instance details | public IPv4 empty | `08-ec2-no-public-ip.png` |
| No internet before NAT | app server → internet | `NO INTERNET` | `12-no-internet.png` |
| Egress through the NAT instance | app server → internet | NAT Elastic IP | `12-nat-ip.png` |
| ALB to the app | browser → ALB | lab page, target `Healthy` | `09-alb-healthy.png`, `09-alb-browser.png` |
| App to database | app server → RDS:3306 | `DB_REACHABLE` | `11-ssm-session.gif` |
| Peering | VPC A → VPC B | ping ok, body `Shared Services` | `14-peering-test.png` |
| Transit Gateway | VPC A → VPC B | ping ok, body `Shared Services` | `15-tgw-test.png` |
| PrivateLink | app server → endpoint DNS | `Shared Services`, `exit=0` | `16-privatelink-curl.png` |
| WireGuard handshake | peer → gateway | handshake under 2 minutes, ping `10.200.0.1` | `20-wireguard-handshake.png` |
| Hybrid reach | peer → app private IP | app page, `exit=0` | `20-wireguard-curl.png` |
| Segmentation (negative) | app server → data subnet on a port other than 3306 | rejected, visible in Flow Logs | `28-recon-in-athena.png` |
