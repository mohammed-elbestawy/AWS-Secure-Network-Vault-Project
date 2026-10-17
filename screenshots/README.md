# Screenshots

Evidence for every step, named after the step that produced it. Cover the **account ID and the email address** in every image before committing it.

| File | What it proves |
|---|---|
| `01-budget.png` | Cost budget with email alert |
| `02-vpc-resource-map.png` | VPC A layout and subnets |
| `03-route-table-data.png` | Data subnets have only a `local` route |
| `04-nacls.png`, `05-security-groups.png` | Layered network controls |
| `06-iam-ssm-role.png` | Instance role for Session Manager |
| `07-ssm-endpoints.png` | Three interface endpoints `Available` |
| `08-ec2-no-public-ip.png` | App server has no public IP |
| `09-alb-healthy.png`, `09-alb-browser.png` | Target `Healthy`, page through the ALB |
| `10-rds-private.png` | Database not publicly accessible |
| `11-ssm-session.gif` | Shell through Session Manager, database reachable |
| `12-no-internet.png`, `12-route-table-with-nat.png`, `12-nat-ip.png` | No egress, then egress through the NAT instance |
| `13-vpc-b-instance.png` | Shared services instance |
| `14-peering.png`, `14-peering-test.png` | Peering and its test |
| `15-tgw-attachments.png`, `15-tgw-route-table.png`, `15-tgw-test.png` | Transit Gateway |
| `16-privatelink-curl.png` | One service exposed through PrivateLink |
| `17-onprem-vpc.png` | Simulated office network |
| `18-wg-server.png`, `19-wg-peer.png` | WireGuard gateway and peer |
| `20-wireguard-handshake.png`, `20-wireguard-curl.png` | Tunnel up, peer reaches the private app |
| `V1-parameters.png` | Four parameters in Parameter Store |
| `V2-vault-service.png`, `V3-smoke-test.png` | Service running, smoke test `10 / 10` |
| `V3B-golden-ami.png`, `V3B-nat-removed.png` | Golden image created, NAT removed |
| `21-s3-files.png`, `21-cloudfront-function.png` | Private site bucket, client-IP function |
| `21-vault-create.png`, `21-vault-reveal.png`, `21-vault-burned.png` | Create, reveal once, link dead |
| `21-project-page.png` | The project page at `/about.html` |
| `22-waf-rate-limit.gif`, `22-waf-xss-403.png`, `22-waf-sampled-requests.png` | WAF rate limit and XSS block |
| `22-waf-blocked.png`, `V4-attack-demo.png` | Attack demo output and blocked requests |
| `23-route53-health.png`, `23-shield-standard.png` | Health check and Shield Standard |
| `24-flowlog-created.png`, `24-flowlogs-in-s3.png` | Flow Logs enabled and delivered |
| `25-athena-rejects.png`, `25-athena-top-talkers.png` | Detection queries |
| `26-tcpdump-mirror.png` | Mirrored VXLAN traffic |
| `27-cloudwatch-alarm.png`, `27-cloudwatch-dashboard.png` | Alarm and dashboard |
| `28-recon-in-athena.png`, `28-isolation-sg-applied.png`, `28-evidence-snapshots.png`, `28-alb-503.png`, `28-incident-response.gif` | Incident drill |
| `29-cost-report.png` | Cost of the build |
| `30-tag-editor-empty.png` | Everything cleaned up |
