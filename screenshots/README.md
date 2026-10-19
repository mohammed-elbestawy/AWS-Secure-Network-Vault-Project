# Screenshots

Evidence for the build, named after the step that produced it. Files marked ★ are shown in `STEPS.md` and `README.md`. The videos are hosted on Google Drive (link in `README.md`). Cover the **account ID and the email address** in every image before committing it.

| File | What it proves |
|---|---|
| `architecture-diagram.png` ★ | Architecture (editable: `architecture-diagram.drawio`) |
| `02-vpc-resource-map.png` ★ | VPC A layout and subnets |
| `03-route-table-data.png` | Data subnets have only a `local` route |
| `04-nacls.png`, `05-security-groups.png` ★ | Layered network controls |
| `07-ssm-endpoints.png` | Three interface endpoints `Available` |
| `08-ec2-no-public-ip.png` ★ | App server has no public IP |
| `09-alb-healthy.png` ★ | Target `Healthy` behind the ALB |
| `10-rds-private.png` | Database not publicly accessible |
| `11-ssm-session.mp4` ★ | Shell through Session Manager, database reachable |
| `12-no-internet.png`, `12-nat-ip.png` ★ | No egress, then egress through the NAT instance |
| `14-peering-test.png` | Peering test |
| `15-tgw-attachments.png`, `15-tgw-test.png` ★ | Transit Gateway |
| `16-privatelink-curl.png` ★ | One service exposed through PrivateLink |
| `20-wireguard-handshake.png` ★, `20-wireguard-curl.png` | Tunnel up, peer reaches the private app |
| `V1-parameters.png` | Four parameters in Parameter Store |
| `V3-smoke-test.png` ★ | Smoke test `10 / 10` |
| `V3B-golden-ami.png`, `V3B-nat-removed.png` | Golden image created, NAT removed |
| `21-vault-create.png` ★, `21-vault-reveal.png`, `21-vault-burned.png` ★ | Create, reveal once, link dead |
| `21-project-page.png` | The project page at `/about.html` |
| `22-waf-rate-limit.mp4` ★, `22-waf-xss-403.png`, `22-waf-sampled-requests.png` | WAF rate limit and XSS block |
| `V4-attack-demo.png` ★ | Attack demo output |
| `23-route53-health.png`, `23-shield-standard.png` | Health check and Shield Standard |
| `24-flowlogs-in-s3.png` | Flow Logs delivered |
| `25-athena-rejects.png` ★ | Detection query |
| `26-tcpdump-mirror.png` ★ | Mirrored VXLAN traffic |
| `27-cloudwatch-alarm.png` ★, `27-cloudwatch-dashboard.png` | Alarm and dashboard |
| `28-recon-in-athena.png`, `28-isolation-sg-applied.png`, `28-evidence-snapshots.png`, `28-alb-503.png` | Incident drill |
| `28-incident-response.mp4` ★ | Incident drill, start to finish |
| `29-cost-report.png` ★ | Cost of the build |
