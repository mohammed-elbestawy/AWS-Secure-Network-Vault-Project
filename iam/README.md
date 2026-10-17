# IAM

| File | Attach to | Purpose |
|---|---|---|
| `vault-instance-policy.json` | The EC2 instance role of the app server | Read the four `/vault/db/*` parameters and decrypt the SecureString, only through SSM |

Replace `ACCOUNT_ID` before creating the policy. The role also keeps `AmazonSSMManagedInstanceCore`
so Session Manager works. Nothing else is granted: the app cannot read Secrets Manager, S3 or any
other parameter path.
