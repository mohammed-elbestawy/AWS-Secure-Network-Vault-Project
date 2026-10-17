# Requirements Coverage

The program brief for **Project 2: Secure AWS Network Architecture & Hybrid Connectivity** has four weeks of tasks and deliverables. This page maps every item to where it lives in the repository and which screenshot proves it. The final submission rules (repository, demo video, screenshots, architecture design, documentation, live demo) are covered at the bottom.

## Week 1 — VPC Core Architecture

| Brief item | Where it is | Evidence |
|---|---|---|
| VPC, public and private subnets | [STEPS.md](../STEPS.md#vpc-a), [NETWORK-PLAN.md](NETWORK-PLAN.md) | `02-vpc-resource-map.png` |
| Route tables, IGW | [NETWORK-PLAN.md](NETWORK-PLAN.md#route-tables) | `03-route-table-data.png`, `12-route-table-with-nat.png` |
| NAT | NAT **instance**, see the note below | `12-no-internet.png`, `12-nat-ip.png` |
| Bastion / SSM access | Session Manager over three interface endpoints, no key pair | `07-ssm-endpoints.png`, `11-ssm-session.gif` |
| EC2, ALB, RDS | [STEPS.md](../STEPS.md#ec2) to [RDS](../STEPS.md#rds) | `08-ec2-no-public-ip.png`, `09-alb-healthy.png`, `10-rds-private.png` |
| Security groups, NACLs, least privilege | [NETWORK-PLAN.md](NETWORK-PLAN.md#security-matrix), [`iam/`](../iam/) | `04-nacls.png`, `05-security-groups.png` |
| Deliverable: architecture diagram | [`architecture/`](../architecture/) | draw.io source and PNG |
| Deliverable: connectivity test results | [NETWORK-PLAN.md](NETWORK-PLAN.md#connectivity-tests) | `09-alb-browser.png`, `11-ssm-session.gif` |

> **NAT instance instead of NAT gateway.** The brief lists a NAT gateway. A NAT instance does the same job, is billed as a `t3.micro`, and exposes the mechanics (IP forwarding, masquerade, source/destination check). The trade-offs (single point of failure, patching, throughput) are written up in [CONCEPTS.md](../CONCEPTS.md#egress-nat-instance-vs-nat-gateway). It is also temporary: the private server only needs egress to install packages.

## Week 2 — Advanced Connectivity and Hybrid Networking

| Brief item | Where it is | Evidence |
|---|---|---|
| VPC peering | [STEPS.md](../STEPS.md#peering) | `14-peering.png`, `14-peering-test.png` |
| VPC endpoints | Three interface endpoints and the S3 gateway endpoint | `07-ssm-endpoints.png` |
| AWS PrivateLink | [STEPS.md](../STEPS.md#privatelink) | `16-privatelink-curl.png` |
| Transit Gateway | [STEPS.md](../STEPS.md#tgw) | `15-tgw-attachments.png`, `15-tgw-route-table.png`, `15-tgw-test.png` |
| Site-to-Site VPN | Implemented with **WireGuard**, compared with the managed service in [HYBRID-AND-EDGE.md](HYBRID-AND-EDGE.md#site-to-site-vpn-vs-wireguard) | `20-wireguard-handshake.png`, `20-wireguard-curl.png` |
| Client VPN, Direct Connect concepts | [HYBRID-AND-EDGE.md](HYBRID-AND-EDGE.md#client-vpn-and-direct-connect) | concept document |
| Test routing and segmentation | [NETWORK-PLAN.md](NETWORK-PLAN.md#connectivity-tests) | `15-tgw-test.png`, `16-privatelink-curl.png` |
| Deliverable: hub-and-spoke / TGW diagram | [`architecture/`](../architecture/) | draw.io source and PNG |
| Deliverable: route table documentation | [NETWORK-PLAN.md](NETWORK-PLAN.md#route-tables) | tables |
| Deliverable: hybrid connectivity test report | [NETWORK-PLAN.md](NETWORK-PLAN.md#connectivity-tests) | `20-wireguard-*.png` |

> **WireGuard instead of Site-to-Site VPN.** A real on-premises network was not available, so the office is a second VPC in another region (`eu-west-1`). WireGuard gives a working encrypted tunnel with a short, auditable configuration. What it gives up (two managed tunnels, BGP, an AWS-managed endpoint) is listed in the comparison document.

## Week 3 — Edge Security, WAF, DDoS and Content Delivery

| Brief item | Where it is | Evidence |
|---|---|---|
| CloudFront with an S3 origin | [STEPS.md](../STEPS.md#cloudfront) | `21-s3-files.png`, `21-vault-create.png` |
| AWS WAF rules | [STEPS.md](../STEPS.md#waf) | `22-waf-rate-limit.gif`, `22-waf-xss-403.png` |
| Shield concepts | [HYBRID-AND-EDGE.md](HYBRID-AND-EDGE.md#ddos-mitigation-plan) | `23-shield-standard.png` |
| Firewall Manager, Global Accelerator comparison | [HYBRID-AND-EDGE.md](HYBRID-AND-EDGE.md#firewall-manager) and [#global-accelerator-vs-cloudfront](HYBRID-AND-EDGE.md#global-accelerator-vs-cloudfront) | concept document |
| Route 53 | Health check on the ALB | `23-route53-health.png` |
| Test edge protections | `code/scripts/attack-demo.sh` | `V4-attack-demo.png`, `22-waf-blocked.png` |
| Deliverable: CloudFront + S3 lab, WAF rule set | [STEPS.md](../STEPS.md#cloudfront) | screenshots above |
| Deliverable: DDoS mitigation plan, edge architecture, Route 53 design | [HYBRID-AND-EDGE.md](HYBRID-AND-EDGE.md) | concept document |

## Week 4 — Network Monitoring, Detection and Incident Response

| Brief item | Where it is | Evidence |
|---|---|---|
| VPC Flow Logs | [STEPS.md](../STEPS.md#flowlogs) | `24-flowlog-created.png`, `24-flowlogs-in-s3.png` |
| Traffic Mirroring | [STEPS.md](../STEPS.md#mirror) | `26-tcpdump-mirror.png` |
| CloudWatch | Alarm, SNS email, dashboard | `27-cloudwatch-alarm.png`, `27-cloudwatch-dashboard.png` |
| Athena log analysis | Saved queries in [DETECTION-AND-IR.md](DETECTION-AND-IR.md#flow-log-queries) | `25-athena-rejects.png`, `25-athena-top-talkers.png` |
| Simulate a compromised instance, isolate, snapshot, collect evidence | [DETECTION-AND-IR.md](DETECTION-AND-IR.md#incident-response-runbook) | `28-*.png`, `28-incident-response.gif` |
| Deliverable: flow log queries, detection use cases | [DETECTION-AND-IR.md](DETECTION-AND-IR.md) | tables |
| Deliverable: IR runbook, evidence collection notes | [DETECTION-AND-IR.md](DETECTION-AND-IR.md#evidence-collection-notes) | `28-evidence-snapshots.png` |
| Deliverable: final secure network report | [FINAL-REPORT.md](FINAL-REPORT.md) | report |

## Submission rules

| Rule | Status |
|---|---|
| GitHub repository with the complete project | This repository |
| Demo video | Linked from the [README](../README.md#demo) |
| Screenshots | [`screenshots/`](../screenshots/) (account ID and email covered) |
| Architecture design | [`architecture/`](../architecture/) |
| Documentation | README, STEPS, CONCEPTS and this `docs/` folder |
| Live project during the session | Run order and talking points in [DEMO-SCRIPT.md](DEMO-SCRIPT.md) |
| Every team member holds the full project data | The repository contains everything needed to rebuild: code, policy, scripts, steps, evidence list |
