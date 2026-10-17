# 🧠 Design Concepts & Rationale

This file explains **why** each decision was made — the questions most likely to come up in a review.

![AWS](https://img.shields.io/badge/AWS-VPC%20%7C%20TGW%20%7C%20PrivateLink-FF9900?style=flat-square&logo=amazonaws&logoColor=white) ![Flask](https://img.shields.io/badge/Backend-Flask-000000?style=flat-square&logo=flask&logoColor=white) ![Region](https://img.shields.io/badge/Region-eu--north--1-232F3E?style=flat-square)

---

### Contents

[![Network](https://img.shields.io/badge/Network_Design-30363D?style=flat-square)](#network) [![CIDR](https://img.shields.io/badge/CIDR_%26_Routes-30363D?style=flat-square)](#cidr) [![Connectivity](https://img.shields.io/badge/Connectivity-30363D?style=flat-square)](#connectivity) [![Hybrid](https://img.shields.io/badge/Hybrid_VPN-30363D?style=flat-square)](#hybrid) [![Edge](https://img.shields.io/badge/Edge_%26_DDoS-30363D?style=flat-square)](#edge) [![Application](https://img.shields.io/badge/Application_%26_Secrets-30363D?style=flat-square)](#app) [![Detection](https://img.shields.io/badge/Detection-30363D?style=flat-square)](#detection) [![IR](https://img.shields.io/badge/Incident_Response-30363D?style=flat-square)](#ir) [![Cost](https://img.shields.io/badge/Cost-30363D?style=flat-square)](#cost)

---

<a id="network"></a>
## 🌐 Network Design

| Question | Answer |
|---|---|
| Why three tiers? | Each tier has a different exposure. Only the ALB needs to be public. The Flask server needs the ALB and nothing else. The database needs the app and nothing else. A mistake or a breach in one tier does not hand over the next. |
| Why do the data subnets have only a `local` route? | The database then has no path to the internet to misconfigure later. Even a wrong security group cannot send data out, because there is no route to send it on. |
| Security group or NACL? | Both, on purpose. A security group is stateful and attached to the interface, so return traffic is allowed automatically. A NACL is stateless and attached to the subnet, so the return path needs its own ephemeral-port rule. If one is configured wrongly, the other still protects. |
| Why chain the security groups (`alb-sg → app-sg → db-sg`)? | Each group allows traffic only from the group before it, not from an address range. The rules keep working if addresses change and they read as the data path. |
| Why Session Manager instead of a bastion host? | No SSH, no key pair, no inbound port and no extra server to patch. Access goes through IAM and is logged. It runs over three interface endpoints, so it works with no internet path at all. |
| Why a NAT instance instead of a NAT gateway? | It does the same job for the price of a `t3.micro` and it shows the mechanics (IP forwarding, masquerade, source/destination check off). The trade-offs are a single point of failure, patching and limited throughput. It is also temporary: the private server only needs egress to install packages. |
| Why must the NAT route be removed before the Flow Log tests? | While it exists, outbound traffic from the private tier succeeds. The "private server cannot call out" test would pass for the wrong reason and the incident drill would show no rejected traffic. |
| Why were the subnet CIDRs rewritten after creating the VPC? | The VPC wizard applied its own CIDRs instead of the typed ones. Every NACL and security group rule depends on the CIDR, so each rule was rewritten against the real values. Resources are identified by CIDR or ID, never by the label. |

---

<a id="cidr"></a>
## 📐 CIDR Plan and Route Tables

Reference tables for the network above. CIDRs do not overlap, which is what makes peering and Transit Gateway routing possible.

**Networks**

| Network | CIDR | Purpose |
|---|---|---|
| VPC A `sn-vpc` | `10.0.0.0/16` | The main application network |
| VPC B `sn-vpc-b` | `10.1.0.0/16` | Shared services, reached through Transit Gateway and PrivateLink |
| On-premises (simulated) `sn-onprem`, `eu-west-1` | `192.168.0.0/16` | Stand-in for an office |
| WireGuard tunnel | `10.200.0.0/24` | Gateway `.1`, peer `.2` |

**Subnets**

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

**Route tables**

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

> The WireGuard gateway masquerades `10.200.0.0/24`, so VPC A needs no route for the tunnel network.

---

<a id="connectivity"></a>
## 🔗 Connectivity: Peering, Transit Gateway, PrivateLink

| Question | Answer |
|---|---|
| Peering or Transit Gateway? | Peering is a direct link between two VPCs and is not transitive. It is the simplest path and was built and tested first. Transit Gateway is a regional hub: attach each VPC once and route through it, so a third network is one more attachment, not a mesh of peering links. Peering was deleted before the Transit Gateway was created so the hub is the only path. |
| Why did the Transit Gateway drop traffic when every route was correct? | A Transit Gateway attachment places an ENI in the subnet, and that subnet's NACL applies to it. Peering places no ENI, which is why the same rules worked before. Reachability Analyzer showed `SUBNET_ACL_RESTRICTION`. Fix: NACL rules for the attachment's own CIDR. |
| Why is PrivateLink needed when the Transit Gateway already connects the VPCs? | They are different designs. The Transit Gateway opens routing between networks. PrivateLink exposes **one service** and nothing else, with no route between the networks. It is the right tool when you want to share a single endpoint, not a network. |
| Why did PrivateLink time out while the target was `Healthy`? | The console attaches a security group to the NLB, and "enforce inbound rules on PrivateLink traffic" applies it to endpoint traffic. Reachability Analyzer said `Reachable` because it cannot see past the endpoint. The test also has to use the **endpoint** DNS name, not the NLB name, because the target is registered by instance ID and the return path differs. |
| Why does VPC B serve a different page from VPC A? | The peering and PrivateLink checks look for the text `Shared Services`. Reusing the VPC A page would make a working test look failed. |

---

<a id="hybrid"></a>
## 🏢 Hybrid Connectivity

| Question | Answer |
|---|---|
| Why WireGuard instead of AWS Site-to-Site VPN? | There was no physical office or customer gateway device, so the "office" is a second VPC in another region. WireGuard shows the same pattern end to end (encrypted tunnel, private reachability, security group and NACL control) with a short, auditable configuration and the cost of one instance. |
| What does WireGuard give up compared with Site-to-Site VPN? | Two managed tunnels in different AZs, BGP route exchange, and an AWS-managed endpoint. The gateway here is a single instance. In production it would be replaced by a Site-to-Site VPN attached to the Transit Gateway. |
| Why does the gateway masquerade `10.200.0.0/24`? | VPC resources then see the gateway's private address as the source, so the VPC needs no extra route for the tunnel network. The gateway also has source/destination check disabled. |
| Why does the office peer initiate the tunnel? | `PersistentKeepalive` on the peer keeps the NAT mapping open, so the gateway only needs to know the peer's key. It also lets the gateway security group allow UDP 51820 from one address only. |
| What are Client VPN and Direct Connect? | Client VPN is a managed OpenVPN-style service for individual users who authenticate with certificates, Active Directory or SAML. Direct Connect is a dedicated or hosted private circuit into AWS with predictable latency. It is not encrypted by default, so a VPN or MACsec goes on top, and it takes weeks to provision. Both are concept items and were not built. |

---

<a id="edge"></a>
## 🌍 Edge Security and DDoS

| Question | Answer |
|---|---|
| Why CloudFront in front of the ALB and S3? | One HTTPS domain serves the static site from S3 and routes `/api/*` to the ALB. The browser crypto API only runs in a secure context, so HTTPS is required. CloudFront also applies the security headers and absorbs floods at the edge instead of at the origin. |
| Why is the S3 bucket private with Origin Access Control? | CloudFront is the only reader. There is no public bucket and no static-website endpoint to bypass the edge protections. |
| Which WAF rules, and why? | The AWS core rule set (SQL injection, XSS, common exploits) plus a rate-based rule of 100 requests per 5 minutes per client. The core set blocks known patterns, the rate rule blocks floods and guessing. |
| Why is the maximum secret size 5,000 bytes? | The core rule set rejects request bodies over 8 KB. A 10,000-byte secret produces a body of about 13.7 KB and would be blocked as an attack. At 5,000 bytes the body is about 6.9 KB. |
| Why does the rate rule count on a header written by a CloudFront Function? | The ALB sees a CloudFront edge address, not the client. `X-Forwarded-For` cannot be trusted because the client can send its own value and the first address is theirs. A viewer-request function overwrites `x-client-ip` with the real viewer address, so the WAF always counts on the true source. |
| Shield Standard or Advanced? | Standard is free and automatic and covers common network and transport floods. Advanced adds a response team, cost protection and richer application-layer visibility for a monthly subscription. The lab uses Standard and lists Advanced as the production step. |
| What would Firewall Manager add? | It applies WAF, Shield Advanced and security group policies across many accounts from one place. It needs AWS Organizations and a delegated administrator, so it is not meaningful in a single account. In a multi-account version this WAF rule set would become one policy applied to every account. |
| Global Accelerator or CloudFront? | CloudFront is a CDN for HTTP with caching and WAF integration. Global Accelerator gives two static anycast IPs for any TCP or UDP traffic and fast regional failover, with no caching. The vault is an HTTP site with static assets, so CloudFront fits. |
| What does the Route 53 health check do here? | It probes the ALB on HTTP 80 every 30 seconds with a failure threshold of 3. In production it would sit behind a failover record that switches to a maintenance page when the check fails. |
| What is the DDoS plan in one line? | Absorb at the edge (CloudFront, Shield), filter at the application layer (WAF rate and managed rules), hide the origin (limit the ALB security group to the CloudFront prefix list, listed as the next step), detect (alarm and WAF metrics), respond (tighten the rate rule, escalate to Shield Advanced). |

---

<a id="app"></a>
## 🔐 Application and Secrets

| Question | Answer |
|---|---|
| How does the server never see the secret? | The browser generates a random AES-256 key, encrypts with AES-GCM and sends only the ciphertext. The key stays in the part of the link after `#`, which browsers never send to a server. |
| Why open a secret in two steps (`status`, then `reveal`)? | Link previews and crawlers fetch URLs. A `GET` with no side effects means they cannot burn a secret. Only `POST /reveal` consumes a view. |
| What if two people open the link at the same instant? | The read and the delete happen in one transaction with a locking read. A test fires 25 simultaneous reveals at one secret and exactly one succeeds. |
| Why Parameter Store instead of Secrets Manager for the app credentials? | It uses the same `ssm` endpoint Session Manager already needs, so no extra endpoint is paid for. The RDS master secret stays in Secrets Manager and is used once to bootstrap the schema. |
| How is the database user limited? | `vault_app` has `SELECT`, `INSERT`, `UPDATE`, `DELETE` on one table and TLS is required. A compromised application cannot read or change anything else. |
| How is the IAM policy limited? | `ssm:GetParameter*` on four parameters only, and `kms:Decrypt` only when the call comes through the SSM service. No wildcard resources. |
| Why does the server validate data that is already ciphertext? | It rejects anything that is not base64url or is too small or too large, so the endpoint cannot be used to store arbitrary data or to probe the parser. |
| Why no inline scripts or styles? | Pages use external files only, so the Content-Security-Policy can be `script-src 'self'; style-src 'self'` and injected inline code would not run. |

---

<a id="detection"></a>
## 📊 Monitoring and Detection

| Question | Answer |
|---|---|
| Flow Logs or Traffic Mirroring? | Flow Logs record metadata (who talked to whom, on which port, accepted or rejected). Traffic Mirroring copies the packets themselves, encapsulated in VXLAN on UDP 4789, to a monitor instance for `tcpdump`. Metadata finds the event, packets explain it. |
| Why Athena? | Flow Logs land in S3. Athena runs SQL on them with no server and no loading step, using partition projection so queries stay cheap. |
| What does the detection query look for? | One source with rejected traffic on more than five distinct ports, which is the shape of a port scan. The same table answers other questions: management ports probed, egress that should not exist, and the largest byte totals. |
| Why alarm on `UnHealthyHostCount`? | It is the earliest signal that the application tier stopped answering the load balancer, whatever the cause. The alarm emails through SNS. |

**Detection use cases**

| Use case | Signal | Response |
|---|---|---|
| Port scan from a compromised host | One source rejected on more than five ports | Isolate the instance, preserve evidence |
| Outbound call-home | Rejected or unexpected egress from the private tier | Isolate, review the process |
| Management port probing | Repeated rejects on 22 or 3389 | Confirm no port is open |
| Data exfiltration | A source and destination pair with unusually large byte totals | Identify the process, block the destination |
| Application outage | `UnHealthyHostCount` above 0 | Check the instance, fail over |
| Web attack | WAF `BlockedRequests` rising | Review sampled requests, tune rules |

---

<a id="ir"></a>
## 🚨 Incident Response

| Question | Answer |
|---|---|
| What is the scenario? | `sn-app-a` is scanning internal addresses and trying to reach the internet. Because the private tier has no egress, the call-home shows up as rejected traffic. |
| Why contain with a security group swap? | An empty `sn-isolation-sg` (no inbound, no outbound) is prepared in advance. Swapping it in stops new connections in seconds without touching the disk. Connections already tracked can continue until they idle out, so for an immediate cut a deny rule at the top of the subnet NACL is added as well. |
| Why not stop or terminate the instance first? | Memory and running processes are evidence. The volume is snapshotted before any change that touches the disk, and the instance is terminated only after the snapshot is `Completed`. |
| How is the service recovered? | A replacement is launched from the golden image taken after the vault was installed. The service starts at boot and reads its settings from Parameter Store, so it needs no internet and no manual install. The isolated instance is deregistered from the target group. |
| What is rotated afterwards? | Anything the instance could read, which here is the database password in Parameter Store. |

**Evidence collection**

| Item | How | Why |
|---|---|---|
| Volume snapshot | Tagged `IncidentStatus=EVIDENCE`, description `IR sn-app-a` | Disk state at isolation, restorable to a forensic instance |
| Console system log | Saved locally as `system-log.txt` | What the instance printed |
| Flow log records | Athena query on the instance address | Network timeline |
| Instance metadata | Instance ID, AMI, subnet, security groups before and after | Scope of the incident |
| Change history | CloudTrail event history | Proves who changed the security group and when |
| Timeline | UTC timestamps: detection, isolation, snapshot complete, recovery | Chain of events |

---

<a id="cost"></a>
## 💰 Cost Decisions

| Question | Answer |
|---|---|
| What bills by the hour? | The NAT instance and its Elastic IP, Transit Gateway attachments, interface endpoints, the ALB, RDS, EC2 and the WAF. None of them has a free tier that covers a multi-day build. |
| How was cost controlled? | A 10 USD monthly budget with an email alert, the build done in the fewest days possible, the NAT removed as soon as the vault was installed, and everything deleted in the final cleanup step in an order that respects dependencies. |
| Why is the WAF deleted when it is not being demoed? | It bills hourly for the Web ACL and its rules whether or not any requests arrive. |
