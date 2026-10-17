# Hybrid Connectivity and Edge Design

Design notes for the parts of the brief that are compared or planned rather than all built. Each section says what was built and what the managed alternative would change.

## Site-to-Site VPN vs WireGuard

| | AWS Site-to-Site VPN | WireGuard (built here) |
|---|---|---|
| Endpoints | AWS-managed virtual private gateway or Transit Gateway attachment | An EC2 instance you run and patch |
| Redundancy | Two tunnels per connection in different AZs | One gateway, single point of failure |
| Routing | Static or BGP, route propagation | Static routes, masquerade on the gateway |
| Crypto | IPsec | ChaCha20-Poly1305, small fixed set |
| Cost | Hourly connection fee plus data transfer | One `t3.micro` plus an Elastic IP |
| Fit | Production, customer gateway devices | Labs, small sites, auditable setups |

Decision: no physical office or customer gateway device was available, so the "office" is a VPC in `eu-west-1`. WireGuard shows the same hybrid pattern end to end (encrypted tunnel, private reachability, security group and ACL control) without the managed service's hourly fee. Moving to the managed service means replacing the gateway instance with a Site-to-Site VPN attached to the Transit Gateway, adding BGP, and deleting the masquerade.

## Client VPN and Direct Connect

**Client VPN** is a managed OpenVPN-style service for individual users. Users authenticate with mutual certificates, Active Directory or SAML, and receive a route into the VPC. It bills per endpoint association hour and per active connection hour. In this design it would replace Session Manager port forwarding for people who need to reach several private resources at once, with authorization rules per group.

**Direct Connect** is a dedicated or hosted private circuit from a data centre into AWS. It gives predictable latency and throughput and keeps traffic off the public internet, but it is not encrypted by default (add MACsec or run a VPN over it) and takes weeks to provision. The resilient pattern is two connections at two locations, with a Site-to-Site VPN as backup. It is a concept item in the brief and was not built.

## DDoS mitigation plan

| Layer | Control | What it stops |
|---|---|---|
| Network and transport (L3/L4) | Shield Standard, automatic on CloudFront, Route 53 and the load balancer | Common volumetric and state-exhaustion floods |
| Absorb at the edge | CloudFront in front, ALB not the only public face | Floods are absorbed by edge locations, not the origin |
| Application (L7) | WAF rate-based rule, AWS managed core rules | Request floods, injection, scanners |
| Origin hiding | ALB security group limited to the CloudFront prefix list (optional hardening) | Bypassing CloudFront to hit the ALB directly |
| Capacity | Auto Scaling on the app tier (improvement), health check and alarm today | Slow degradation under load |
| Detection | CloudWatch alarm on unhealthy targets, WAF `BlockedRequests` on the dashboard, Route 53 health check | Knowing an attack is under way |
| Response | Tighten the rate rule, block offending ranges, escalate to Shield Advanced if sustained | Reducing impact quickly |

Shield Advanced adds a response team, cost protection and richer L7 visibility, for a monthly subscription. It was left out of the lab and is the next step for a production workload.

## Firewall Manager

Firewall Manager applies WAF, Shield Advanced, security group, Network Firewall and DNS Firewall policies across many accounts from one place. It needs AWS Organizations and a delegated administrator account, so it is not meaningful in a single-account lab. In a multi-account version, the WAF rule set from this project would become one Firewall Manager policy applied to every account's load balancers and CloudFront distributions, with non-compliant resources reported automatically.

## Global Accelerator vs CloudFront

| | CloudFront | Global Accelerator |
|---|---|---|
| What it is | CDN with caching and edge compute | Two static anycast IPs that carry traffic over the AWS backbone |
| Protocols | HTTP and HTTPS (and WebSocket) | Any TCP or UDP |
| Caching | Yes | No |
| Origins | S3, ALB, custom HTTP | ALB, NLB, EC2, Elastic IP |
| Best for | Static content, cacheable APIs, HTTP protection with WAF | Non-HTTP workloads, static IP allow-lists, fast regional failover |

Decision: the vault is an HTTP site with static assets, so CloudFront gives caching, a single HTTPS domain and WAF integration. Global Accelerator would add value if the service needed fixed IPs or multi-region failover.

## Route 53 and health check design

A health check probes the ALB on HTTP 80, path `/`, every 30 seconds, with a failure threshold of 3. The lab only observes it. In a production design it would sit behind a failover or latency record set: a primary record pointing at the CloudFront distribution and a secondary record pointing at a static maintenance page, switching automatically when the check fails.
