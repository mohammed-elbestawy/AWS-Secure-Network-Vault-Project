# Screenshots

Evidence for the build, named after the step that produced it. Cover the **account ID and the email address** in every image before committing it.

| File | What it proves | Shown in |
|---|---|---|
| `architecture-diagram.png` | Architecture (editable source: `architecture-diagram.drawio`) | README |
| `02-vpc-resource-map.png` | VPC A layout and subnets | STEPS |
| `11-ssm-session.mp4` | Shell through Session Manager with no key, database reachable | README, STEPS |
| `15-tgw-test.png` | Transit Gateway: ping and curl succeed after the NACL fix | STEPS |
| `16-privatelink-curl.png` | One service exposed through PrivateLink | STEPS |
| `20-wireguard-handshake.png` | Tunnel up, handshake under two minutes | STEPS |
| `21-vault-create.png` | A secret created through CloudFront | STEPS |
| `21-vault-burned.png` | The link is dead after one reveal | STEPS |
| `22-waf-rate-limit.mp4` | 250 requests: `200`, then `403` once the rate rule trips | README, STEPS |
| `V4-attack-demo.png` | Attack demo output | README |
| `25-athena-rejects.png` | Detection query on rejected traffic | STEPS |
| `28-incident-response.mp4` | Incident drill: the instance isolated by a security group swap | README, STEPS |
| `29-cost-report.png` | Cost of the build | STEPS |
