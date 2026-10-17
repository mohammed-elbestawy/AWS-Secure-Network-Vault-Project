# Final Secure Network Report

## Summary

A three-tier private network on AWS, protected at the edge, connected to a simulated office, monitored end to end, and carrying a real application: a zero-knowledge secret-sharing service. The design assumes every individual control can fail, so independent layers back each other up. Every layer was tested, and the faults found along the way are documented.

## Scope

| Area | Included |
|---|---|
| Regions | `eu-north-1` (network, application), `eu-west-1` (simulated office) |
| Networks | VPC A (three tiers), VPC B (shared services), simulated on-premises network |
| Connectivity | Peering (then replaced), Transit Gateway, PrivateLink, WireGuard tunnel |
| Edge | CloudFront, S3 (private), WAF, Shield Standard, Route 53 health check |
| Application | Flask API, RDS MySQL, browser-side AES-256-GCM |
| Operations | Session Manager, Parameter Store, Flow Logs, Athena, Traffic Mirroring, CloudWatch, SNS |
| Not included | Multi-account governance, Direct Connect, Client VPN (concept only, see [HYBRID-AND-EDGE.md](HYBRID-AND-EDGE.md)) |

## Controls and how they were verified

| Layer | Control | Verified by |
|---|---|---|
| Exposure | App and data tiers have no public IP, data subnets have only a local route | `08-ec2-no-public-ip.png`, `03-route-table-data.png` |
| Access | Session Manager through VPC endpoints, no SSH, no key pair | `11-ssm-session.gif` |
| Segmentation | Security groups chained alb → app → db, NACLs on every tier | `04-nacls.png`, `05-security-groups.png`, Athena rejects |
| Least privilege | DB user limited to one table, IAM policy limited to four parameters | [`iam/`](../iam/), `V1-parameters.png` |
| Secrets | Database password in Parameter Store, none in code or user data | `V1-parameters.png` |
| Edge | WAF core rules and a rate rule, security headers and CSP from CloudFront | `22-waf-*.png`, `V4-attack-demo.png` |
| Application | Input validation, parameterised SQL, atomic read-and-burn, encrypted in the browser | 29 backend and 10 crypto tests, `V3-smoke-test.png` |
| Hybrid | Encrypted tunnel, source-restricted security group, NACL rule limited to one address | `20-wireguard-*.png` |
| Detection | Flow Logs, Athena queries, mirror to a monitor, alarm and email | `25-*.png`, `26-tcpdump-mirror.png`, `27-*.png` |
| Response | Isolation group, snapshot, evidence notes, recovery | `28-*.png` |

## Findings during the build

1. **Transit Gateway dropped traffic with correct routes.** The attachment places an interface in the app subnet, so that subnet's NACL applies. Peering does not, which is why the same rules had worked before. Fix: NACL rules for the subnet's own CIDR.
2. **PrivateLink timed out with a healthy target.** The NLB's own security group blocked client traffic, and the option to enforce inbound rules on PrivateLink traffic was on. Reachability Analyzer reported `Reachable` because it cannot see past the endpoint.
3. **Session Manager offline.** The app security group had no outbound 443 to the VPC and the endpoint group needed inbound 443.
4. **Subnet CIDRs were not the ones typed.** The VPC wizard applied defaults, so every rule was written against the real CIDRs.
5. **The WAF would have blocked larger secrets.** The core rule set rejects request bodies over 8 KB. A 10,000-byte secret produces a body of about 13.7 KB, so the application limit was lowered to 5,000 bytes (about 6.9 KB), which passes.
6. **A rate limit keyed on `X-Forwarded-For` can be dodged.** A client can send its own header and the first address is theirs. Hardening: a CloudFront Function overwrites a custom header with the real viewer address and the WAF rule aggregates on that header ([`cloudfront-client-ip.js`](../code/infra/cloudfront-client-ip.js)).

## Residual risks

| Risk | Impact | Next step |
|---|---|---|
| CloudFront to ALB uses HTTP | Traffic between them is not encrypted in transit | ACM certificate on the ALB, HTTPS-only origin |
| ALB reachable directly | A client can bypass CloudFront and its protections | Limit the ALB security group to the CloudFront prefix list |
| Single NAT instance and single WireGuard gateway | One failure removes egress or the tunnel | Managed NAT gateway, Site-to-Site VPN, second AZ |
| Single-AZ database | An AZ failure takes the data tier down | Multi-AZ RDS |
| No threat-intelligence layer | Known-bad addresses are not blocked | GuardDuty, WAF managed IP reputation list |
| Manual password rotation | Long-lived database credential | Rotation with Secrets Manager |

## Cost

Hourly billed items: NAT instance and its Elastic IP, Transit Gateway attachments, interface endpoints, ALB, RDS, EC2, WAF. The build is run in the fewest days possible and everything is deleted in the final step ([STEPS.md](../STEPS.md#cleanup)). A cost report screenshot (`29-cost-report.png`) closes the evidence.

## Conclusion

The network meets the brief's four stages: a three-tier VPC with least-privilege rules, advanced and hybrid connectivity, edge security with a tested WAF, and monitoring with a rehearsed incident response. The deliberate substitutions (NAT instance, WireGuard) are documented with their trade-offs.
