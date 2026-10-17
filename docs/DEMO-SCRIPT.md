# Live Demo Script

About 12 minutes. Every step names the screen to have open and what to say. Build everything the day before and run the checklist in the morning.

## Before the session

- [ ] RDS is `Available` (start it if it was stopped)
- [ ] Target group `sn-app-tg` is `Healthy`
- [ ] The CloudFront URL opens over HTTPS and the vault creates a link
- [ ] Browser tabs ready: CloudFront site, EC2 instance list, VPC route tables, Transit Gateway, WAF sampled requests, Athena, CloudWatch dashboard
- [ ] A terminal with `attack-demo.sh` and a Session Manager session on the peer, in a text file ready to paste
- [ ] Screenshots and GIFs from `screenshots/` open in a folder as a fallback if a live step fails
- [ ] NAT route and the wide HTTPS rule are removed (otherwise the reject tests lie)

## Run order

| Time | Show | Say |
|---|---|---|
| 0:00 | Architecture diagram | The request path, the three tiers, what is public and what is not |
| 1:30 | The site on CloudFront: create a secret, open the link, refresh | The browser encrypts, the key never leaves it, the record burns on read |
| 3:00 | EC2 list (no public IP), Session Manager session | No SSH, no key, no inbound port. The server is reachable only through endpoints |
| 4:00 | Route tables: data subnets with only `local`, then the Transit Gateway route table | Segmentation by design, hub-and-spoke between VPCs |
| 5:00 | Ping and curl from the app server to VPC B, then the PrivateLink curl | TGW opens routing, PrivateLink exposes one service only |
| 6:30 | WireGuard peer: `wg show`, then `curl` to the private app | Hybrid connectivity, encrypted tunnel, source-restricted rules |
| 7:30 | `attack-demo.sh`, then WAF sampled requests | Injection and scanning blocked, the app also rejects them on its own |
| 9:00 | Athena: rejected traffic and the port scan query | Detection from Flow Logs |
| 10:00 | Isolation: swap the security group, show the ALB `503`, the alarm email | Contain, preserve, recover |
| 11:30 | Cost report and the cleanup list | Everything hourly is removed at the end |

## If something fails live

- Say what the check does and why it should pass, then show the screenshot or GIF for that step.
- Use the debugging order from [STEPS.md](../STEPS.md): AZ, route table, return route, security group both ways, NACL both ways, Reachability Analyzer.
