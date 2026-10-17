# 🔐 AWS Secure Network Architecture — Zero-Knowledge Secret Vault

A three-tier private network on AWS with a real application on top of it: a zero-knowledge secret-sharing service where the server never sees the secret. Built and tested step by step, including the faults I hit on the way.

**Live demo:** https://REPLACE-WITH-CLOUDFRONT-DOMAIN.cloudfront.net  ·  **Demo video:** https://youtu.be/REPLACE-WITH-VIDEO-ID

![AWS](https://img.shields.io/badge/AWS-VPC%20%7C%20TGW%20%7C%20PrivateLink-FF9900?style=flat-square&logo=amazonaws&logoColor=white)
![Flask](https://img.shields.io/badge/Backend-Flask-000000?style=flat-square&logo=flask&logoColor=white)
![JavaScript](https://img.shields.io/badge/Frontend-HTML%20%7C%20CSS%20%7C%20JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![WireGuard](https://img.shields.io/badge/VPN-WireGuard-88171A?style=flat-square&logo=wireguard&logoColor=white)
![CI](https://github.com/mohammed-elbestawy/AWS-Secure-Network-Vault-Project/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

```
Network      VPC A (public / app / data tiers) · VPC B (shared services) · simulated on-prem
Connectivity Transit Gateway · PrivateLink · WireGuard tunnel · NAT instance
Application  Zero-knowledge secret vault: Flask API + HTML/CSS/JavaScript + MySQL on RDS
Protection   CloudFront · WAF · Shield · security groups and NACLs on every tier
Operations   Session Manager · Parameter Store · CloudWatch · Flow Logs + Athena · Traffic Mirroring
Tests        29 backend · 10 crypto · end-to-end · shell syntax — run in CI
```

---

## 📋 Contents

1. [Demo](#-demo)
2. [The Problem](#-the-problem)
3. [Architecture](#-architecture)
4. [Requirements Coverage](#-requirements-coverage)
5. [The Vault](#-the-vault)
6. [Security Decisions](#-security-decisions)
7. [Tests](#-tests)
8. [Problems Found While Building](#-problems-found-while-building)
9. [Cost and Cleanup](#-cost-and-cleanup)
10. [Possible Improvements](#-possible-improvements)
11. [Documentation](#-documentation)
12. [Repository Structure](#-repository-structure)

---

## 🎬 Demo

| | |
|---|---|
| Live site | `https://<cloudfront-domain>` — the vault at `/`, the project page at `/about.html` |
| Demo video | Walkthrough of the build, the vault, the attack demo and the incident drill |
| Screenshots | [`screenshots/`](screenshots/), named after the step that produced them |
| Run order for a live session | [`docs/DEMO-SCRIPT.md`](docs/DEMO-SCRIPT.md) |

---

## 🎯 The Problem

A public web application is exposed to guessing, injection, scanning and credential theft. One control is never enough, so the design stacks independent layers and assumes each one can fail.

| Risk | How it is handled |
|---|---|
| Direct access to servers or the database | App and data tiers are private: no public IP, data subnets have no route to the internet |
| SSH keys and open management ports | Session Manager over VPC endpoints, no inbound port, no key pair |
| Injection and abuse on the web tier | WAF managed rules and a rate-based rule, strict input validation, parameterised SQL |
| A database or server breach leaking secrets | Secrets are encrypted in the browser. The server only holds ciphertext |
| Over-privileged application | Dedicated DB user with rights on one table, an IAM policy limited to four parameters |
| Lateral movement between networks | Transit Gateway routes and PrivateLink expose only what is needed |
| Not knowing something happened | Flow Logs, Athena, Traffic Mirroring, CloudWatch alarm and SNS email |

---

## 🏗️ Architecture

![Architecture](architecture/AWS-Secure-Architecture.png)

The editable version is [`architecture/AWS-Secure-Architecture.drawio`](architecture/AWS-Secure-Architecture.drawio) (open it in diagrams.net).

**Request path**

```
User → CloudFront ─┬─ /*      → S3 (private bucket, Origin Access Control)
                   └─ /api/*  → WAF → ALB → Flask EC2 (private) → RDS MySQL (TLS)
Admin → Session Manager → VPC endpoints → Flask EC2
On-prem peer ⇄ WireGuard gateway (UDP 51820) → VPC A
VPC A ⇄ Transit Gateway ⇄ VPC B     ·     VPC A → PrivateLink → one service in VPC B
```

| Layer | Services |
|---|---|
| Edge | CloudFront, S3, WAF, Shield Standard, Route 53 health check |
| Network | VPC, public/private subnets, Internet gateway, NAT instance, VPC endpoints, Transit Gateway, PrivateLink, NLB |
| Compute | EC2 (Flask API, WireGuard gateway, NAT instance, monitor, shared service) |
| Data | RDS MySQL, S3 (Flow Logs) |
| Access and secrets | Session Manager, Parameter Store (SecureString), IAM |
| Observability | VPC Flow Logs, Athena, Traffic Mirroring, CloudWatch, SNS |

---

## 📌 Requirements Coverage

The project follows the four stages of the program brief. The full item-by-item mapping, with the evidence file for each, is in [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md).

| Stage | What was delivered | Details |
|---|---|---|
| 1. VPC core | Three-tier VPC, route tables, IGW, NAT instance, Session Manager, EC2, ALB, RDS, security groups, NACLs | [`docs/NETWORK-PLAN.md`](docs/NETWORK-PLAN.md) |
| 2. Connectivity | Peering, endpoints, PrivateLink, Transit Gateway, WireGuard tunnel to a simulated office, Client VPN and Direct Connect compared | [`docs/HYBRID-AND-EDGE.md`](docs/HYBRID-AND-EDGE.md) |
| 3. Edge security | CloudFront with S3, WAF, Shield, Route 53 health check, attack simulation, Firewall Manager and Global Accelerator compared | [`docs/HYBRID-AND-EDGE.md`](docs/HYBRID-AND-EDGE.md) |
| 4. Monitoring and IR | Flow Logs, Athena queries, Traffic Mirroring, CloudWatch, compromised-instance drill with isolation, snapshot and evidence | [`docs/DETECTION-AND-IR.md`](docs/DETECTION-AND-IR.md) |
| Final report | Controls, findings, residual risks, cost | [`docs/FINAL-REPORT.md`](docs/FINAL-REPORT.md) |

Two deliberate substitutions, each documented with its trade-offs: a **NAT instance** instead of a NAT gateway, and **WireGuard** instead of AWS Site-to-Site VPN.

---

## 🧠 The Vault

The browser encrypts, the server stores noise.

```
https://host/view.html?id=ID#KEY

ID   192 random bits, picks the record, decrypts nothing
KEY  256-bit AES key, after "#", never sent to any server

create  browser: key = random(256) → AES-GCM(pad(secret)) → POST ciphertext
reveal  browser: POST /reveal → ciphertext (record deleted in the same transaction) → decrypt with KEY
```

- **Two-step open.** `GET /status` has no side effects, `POST /reveal` consumes a view. Link previews and crawlers cannot burn a secret.
- **Atomic read and burn.** `SELECT ... FOR UPDATE` then delete in one transaction. A concurrency test fires 25 simultaneous reveals at one secret and exactly one succeeds.
- **Padding.** Plaintext is length-prefixed and padded to 256-byte blocks, so the stored size does not reveal the exact length.
- **Size limit.** A secret is limited to 5,000 bytes. The request body then stays under the 8 KB limit of the WAF core rule set, so a legitimate secret is never blocked.
- **No inline code.** Pages use external scripts and styles only, so the CSP is `script-src 'self'; style-src 'self'`.
- **Logs.** Only the first six characters of an id are written, never the full id.

The browser crypto API requires a secure context, so the site must be opened over HTTPS (CloudFront) or `localhost` (Session Manager port forwarding).

---

## 🔒 Security Decisions

| Decision | Why |
|---|---|
| Client-side AES-256-GCM, key in the URL fragment | A server or database breach exposes nothing readable |
| Parameter Store instead of Secrets Manager for the app credentials | It rides on the `ssm` endpoint Session Manager already needs, so no extra endpoint is paid for. The RDS master secret stays in Secrets Manager and is used once to bootstrap the schema |
| Least-privilege DB user (`SELECT/INSERT/UPDATE/DELETE` on one table), TLS required | A compromised app cannot read or change anything else |
| WAF rate rule aggregated on a header written by a CloudFront Function | With CloudFront in front, the connecting IP is a CloudFront edge. `X-Forwarded-For` is client-controlled, so a function overwrites `x-client-ip` with the real viewer address |
| NAT instance, temporary | Cheaper than a managed NAT gateway for a lab, and it makes the mechanics visible. It is removed before the logging tests |
| WireGuard instead of Site-to-Site VPN | Small, auditable, quick to build. It gives up the managed dual-tunnel redundancy |
| NACL rules on every subnet that hosts an ENI | Transit Gateway attachments and interface endpoints are filtered by the subnet's NACL |
| Strict input validation on a blob that is already ciphertext | The server rejects anything that is not base64url, too small or too large |

---

## ✅ Tests

Run locally and in CI (`.github/workflows/ci.yml`):

```bash
python -m unittest discover -s code/tests -v     # 29 tests: API, validation, concurrency, MySQL transaction flow
node --test code/tests/crypto.test.mjs           # 10 tests: round trip, tamper, wrong key, padding, limits
BASE_URL=http://127.0.0.1:8099 node code/tests/e2e-local.mjs   # browser crypto + real HTTP API
bash code/scripts/smoke-test.sh http://localhost                # 10 checks against a running instance
```

The MySQL path is exercised against a fake DB-API connection (locking read, burn, rollback). It does not replace a test on a real database, which is covered by the AWS run below.

**End-to-end on AWS** (screenshots in [`screenshots/`](screenshots/))

| Check | Evidence | Status |
|---|---|---|
| Private server reachable only through Session Manager | `11-ssm-session.gif` | ✅ |
| Egress through the NAT instance, then removed | `12-nat-ip.png`, `V3B-nat-removed.png` | ✅ |
| VPC A to VPC B through the Transit Gateway | `15-tgw-test.png` | ✅ |
| One service exposed through PrivateLink | `16-privatelink-curl.png` | ✅ |
| WireGuard tunnel up, on-prem peer reaches the private app | `20-wireguard-handshake.png`, `20-wireguard-curl.png` | ✅ |
| Vault: create, reveal once, link dead afterwards | `21-vault-create.png`, `21-vault-reveal.png`, `21-vault-burned.png` | ✅ |
| WAF blocks SQLi and XSS probes, rate limit trips | `22-waf-rate-limit.gif`, `22-waf-blocked.png`, `V4-attack-demo.png` | ✅ |
| Rejected traffic found with Athena | `25-athena-rejects.png` | ✅ |
| Compromised instance isolated, evidence kept, service recovered | `28-incident-response.gif`, `28-evidence-snapshots.png` | ✅ |

---

## 🐛 Problems Found While Building

These cost real time and are the most useful part of the project.

1. **Transit Gateway: routes all correct, traffic still dropped.** Reachability Analyzer reported `SUBNET_ACL_RESTRICTION`. A TGW attachment places an ENI in the subnet, so the subnet's NACL applies. VPC peering does not, which is why the same rules worked before. Fix: NACL rules for the subnet's own CIDR.
2. **PrivateLink timing out with a healthy target.** The NLB had a security group that did not allow the client traffic, and "enforce inbound rules on PrivateLink traffic" applies it to endpoint traffic. Reachability Analyzer said `Reachable` because it cannot see past the endpoint.
3. **Session Manager offline.** The agent timed out on the `ssm` endpoint: the app security group had no outbound 443 to the VPC, and the endpoint security group needed inbound 443.
4. **Subnet CIDRs not as written.** The VPC wizard used its defaults, so every NACL and security group rule had to be rewritten against the real CIDRs.
5. **A placeholder pasted literally** (`DB_ENDPOINT`) produced a misleading DNS error. Test commands now use `curl -m 5 -sS ...; echo "exit=$?"` so failures are visible.
6. **The WAF would have blocked larger secrets.** The core rule set rejects bodies over 8 KB and a 10,000-byte secret makes a 13.7 KB body. The application limit is now 5,000 bytes.
7. **A rate limit on `X-Forwarded-For` can be dodged,** because the client can send its own value. A CloudFront Function now overwrites a header with the real viewer address and the WAF counts on that.

---

## 💰 Cost and Cleanup

Hourly billed: NAT instance and its Elastic IP, Transit Gateway attachments, interface endpoints, ALB, RDS, EC2. Stop RDS when pausing. Two items must be removed before the logging tests or they invalidate them: the default route to the NAT instance and the `HTTPS 0.0.0.0/0` rule on the app security group. The full cleanup order is in `STEPS.md` (Step 30).

---

## 🚀 Possible Improvements

- ACM certificate on the ALB and HTTPS-only CloudFront origin
- Optional passphrase on top of the link key
- A security group limited to the CloudFront prefix list so the ALB cannot be reached directly
- Multi-AZ RDS, GuardDuty, and automatic rotation of the app DB password
- Infrastructure as code (Terraform) for the whole stack
- Application logs to CloudWatch with the agent (config included in `code/deploy/`, needs the `logs` endpoint)

---

## 📚 Documentation

| File | Purpose |
|---|---|
| [`STEPS.md`](STEPS.md) | Every console step, in order, with the checks and screenshots |
| [`CONCEPTS.md`](CONCEPTS.md) | What each AWS service is and why it is used here |
| [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) | Program brief mapped to files and evidence |
| [`docs/NETWORK-PLAN.md`](docs/NETWORK-PLAN.md) | CIDR plan, route tables, security matrix, connectivity tests |
| [`docs/HYBRID-AND-EDGE.md`](docs/HYBRID-AND-EDGE.md) | VPN comparison, DDoS plan, Firewall Manager, Global Accelerator |
| [`docs/DETECTION-AND-IR.md`](docs/DETECTION-AND-IR.md) | Athena queries, detection use cases, IR runbook, evidence notes |
| [`docs/FINAL-REPORT.md`](docs/FINAL-REPORT.md) | The final secure network report |
| [`docs/DEMO-SCRIPT.md`](docs/DEMO-SCRIPT.md) | Live session run order |
| [`iam/`](iam/) | The instance policy |
| [`screenshots/README.md`](screenshots/README.md) | Evidence list |

---

## 📁 Repository Structure

```
AWS-Secure-Network-Vault-Project/
├── README.md
├── STEPS.md
├── CONCEPTS.md
├── LICENSE
├── architecture/        draw.io source and PNG
├── docs/                requirements map, network plan, edge design, detection and IR, report, demo script
├── iam/                 instance policy
├── screenshots/         evidence (account id and email covered)
├── .github/workflows/   CI
└── code/
    ├── backend/         Flask API, store, validation, schema
    ├── frontend/        HTML, CSS, JavaScript (create, view, security and project pages)
    ├── deploy/          install script, systemd units, CloudWatch agent config
    ├── infra/           NAT instance, WireGuard and CloudFront function
    ├── scripts/         DB bootstrap, smoke test, attack demo
    └── tests/           API, crypto, end-to-end
```

Built by Mohammed Elbestawy · [GitHub](https://github.com/mohammed-elbestawy) · [LinkedIn](https://linkedin.com/in/mohammed-elbestawy-4349a7328)
