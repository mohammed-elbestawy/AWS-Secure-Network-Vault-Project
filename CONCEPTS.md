# Concepts behind the design

Short explanations of the choices in this project. Written to be read before a review or an interview.

## Network layout
- **VPC / subnets.** A VPC is a private network. A subnet is public only because its route table has a route to an Internet Gateway. The ALB sits in public subnets; the app and the database sit in private subnets with no public IP.
- **Three tiers.** Public (ALB, NAT instance, WireGuard gateway), app (Flask), data (RDS). The data subnets have only the `local` route, so there is no path to the internet at all.

## Security groups vs NACLs
- A **security group** is stateful and attached to an ENI. Return traffic is allowed automatically. Rules reference other groups (`alb-sg` -> `app-sg` -> `db-sg`).
- A **NACL** is stateless and attached to a subnet. Return traffic needs its own rule (ephemeral ports 1024-65535). It is a second layer that still protects when a group is misconfigured.
- Anything that puts an ENI inside a subnet (Transit Gateway attachment, interface endpoint, load balancer) is subject to that subnet's NACL. A missing NACL rule for the TGW attachment caused this project's hardest-to-find fault.

## Reaching the instance without SSH
- **Session Manager** gives a shell through IAM, with no inbound port and no key pair. It works in a private subnet through three interface endpoints (`ssm`, `ssmmessages`, `ec2messages`).
- **Port forwarding** over Session Manager exposes the app on `localhost` of the admin's laptop, which is also a secure context for the browser crypto API.

## Egress: NAT instance vs NAT gateway
- A **NAT gateway** is managed, scales and is highly available, but bills hourly plus per GB.
- A **NAT instance** is an EC2 instance running IP forwarding and masquerade. It is cheaper for a lab and teaches how NAT works. The trade-offs: you patch and size it, it is a single point of failure, and source/destination check must be disabled on it.
- Here it is temporary: the private app instance needs egress only to install packages. It is removed before the logging tests so rejected outbound traffic shows up correctly.

## Connecting networks
- **VPC Peering:** direct, simple, not transitive.
- **Transit Gateway:** a hub. Scales to many VPCs and supports transitive routing.
- **PrivateLink:** exposes one service (an NLB) to another VPC without opening the networks to each other.

## Hybrid connectivity: WireGuard instead of Site-to-Site VPN
- The simulated on-prem network connects to VPC A over a **WireGuard** tunnel (UDP 51820) between two EC2 instances. WireGuard has a tiny codebase, modern fixed cryptography, and a short config. It trades away what the managed Site-to-Site VPN gives: no built-in redundancy (two tunnels) and no AWS-managed endpoint.
- The gateway masquerades tunnel traffic, so VPC resources see the gateway's private IP and no extra routes are needed. A routed design (route entries to the gateway ENI) is the next step.

## Edge and application protection
- **CloudFront** serves the static site from a private S3 bucket (Origin Access Control) and forwards `/api/*` to the ALB. One HTTPS domain, no CORS.
- **WAF** on the ALB applies the managed core rules and a rate-based rule. Because CloudFront sits in front, the rate rule aggregates on the `X-Forwarded-For` client IP, not on the connecting IP.
- **Shield Standard** is automatic.

## The vault
- The browser generates a 256-bit key and encrypts with AES-GCM. The key travels in the URL fragment (`#...`), which browsers never send to the server.
- The server stores ciphertext, an expiry and a view counter. Read and delete happen in one transaction (`SELECT ... FOR UPDATE`), so concurrent readers cannot both win.
- Opening a link is two calls: `status` (no side effects) and `reveal` (consumes a view). Link previews and crawlers cannot burn a secret.
- Database credentials are in **SSM Parameter Store** (SecureString), read through the same `ssm` interface endpoint Session Manager already needs. That avoids a separate Secrets Manager endpoint. The RDS master secret stays in Secrets Manager and is used only for the one-time schema bootstrap.

## Observation and response
- **Flow Logs + Athena** answer "who was rejected, and from where".
- **Traffic Mirroring** copies packets to a monitoring instance for inspection.
- **CloudWatch** holds the dashboard and the alarm on unhealthy targets; **SNS** emails it.
- **Incident response** isolates a suspect instance by swapping its security group and snapshotting its volume for investigation.

## Edge hardening details
- **CloudFront Function.** A tiny script that runs at the edge on every `/api/*` request. It writes the real viewer address into `x-client-ip`, replacing anything the client sent. `X-Forwarded-For` cannot be trusted for this because the client controls its first value.
- **WAF body size.** The core rule set blocks request bodies over 8 KB. The vault limits a secret to 5,000 bytes so its request body (about 6.9 KB) is never blocked by mistake.

## Recovery
- **Golden image.** An AMI taken after the vault is installed. The service starts at boot and reads its settings from Parameter Store, so a replacement instance needs no internet and no manual install. It turns the incident-response recovery into a single launch.

## Services at a glance

| Service | What it is | Why it is used here | Without it |
|---|---|---|---|
| VPC, subnets, route tables | A private network and its traffic rules | Three tiers with different exposure | No isolation |
| Internet gateway | The VPC's door to the internet | Only the public tier routes to it | No public entry |
| NAT instance | A server that forwards outbound traffic | Temporary egress for installs | Private servers cannot install packages |
| Security groups | Stateful firewall per interface | Chain alb → app → db, least privilege | Flat network |
| Network ACLs | Stateless firewall per subnet | Second layer, protects against SG mistakes | One control to fail |
| EC2 | Virtual servers | Flask API, gateways, monitor | No compute |
| ALB | HTTP load balancer | Public entry to the private app, health checks | App must be public |
| RDS MySQL | Managed database | Stores ciphertext in the data tier | Self-managed DB |
| Systems Manager Session Manager | Shell through IAM | No SSH, no key, no open port | Bastion host and keys |
| VPC interface and gateway endpoints | Private paths to AWS services | Session Manager and S3 without internet | Needs NAT for AWS APIs |
| Parameter Store | Encrypted configuration | DB password read at start, never on disk | Secret in code or user data |
| IAM | Identity and permissions | Instance role and a four-parameter policy | Over-privileged server |
| VPC peering | Direct link between two VPCs | Simplest path, built then replaced | n/a |
| Transit Gateway | Regional routing hub | Hub-and-spoke between VPCs | Mesh of peering links |
| PrivateLink | One service shared privately | Expose a single service, not a network | Open both networks |
| WireGuard | Lightweight VPN | Encrypted tunnel to a simulated office | No hybrid link |
| S3 | Object storage | Private static site and Flow Log storage | Web server needed |
| CloudFront | CDN | One HTTPS domain, serves S3 and routes the API | No edge layer |
| WAF | Web application firewall | Injection and rate protection | Attacks reach the app |
| Shield Standard | Automatic DDoS protection | Free baseline at the edge | Exposed to floods |
| Route 53 health check | Endpoint monitor | Observes the ALB | No availability signal |
| VPC Flow Logs | Records of accepted and rejected flows | Evidence and detection | Blind network |
| Athena | SQL over S3 | Query the logs | Manual log reading |
| Traffic Mirroring | Packet copies to an instance | Deep inspection | Only metadata |
| CloudWatch and SNS | Metrics, alarms, email | Alert on unhealthy targets | Silent failure |
| EBS snapshots | Disk backups | Evidence in the incident drill | No forensic copy |
