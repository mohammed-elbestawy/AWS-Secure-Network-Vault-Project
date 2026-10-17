# Detection and Incident Response

Flow log queries, detection use cases, the compromised-instance runbook and the evidence collection notes. Everything here was exercised in the build (Steps 24 to 28).

## Flow log queries

Run in Athena against `sn_logs.vpc_flow_logs` (see [STEPS.md](../STEPS.md#flowlogs) for the table definition). Replace `APP_IP` and `GATEWAY_IP` with real private addresses.

**1. Rejected traffic, noisiest pairs first**

```sql
SELECT srcaddr, dstaddr, dstport, protocol, count(*) AS hits, sum(bytes) AS bytes
FROM sn_logs.vpc_flow_logs
WHERE action = 'REJECT' AND "date" >= current_date - interval '1' day
GROUP BY srcaddr, dstaddr, dstport, protocol
ORDER BY hits DESC
LIMIT 25;
```

**2. Port scan: one source, many rejected ports**

```sql
SELECT srcaddr, dstaddr, count(DISTINCT dstport) AS ports_tried, count(*) AS attempts
FROM sn_logs.vpc_flow_logs
WHERE action = 'REJECT' AND "date" >= current_date - interval '1' day
GROUP BY srcaddr, dstaddr
HAVING count(DISTINCT dstport) > 5
ORDER BY ports_tried DESC;
```

**3. Management ports probed from outside**

```sql
SELECT srcaddr, dstport, count(*) AS attempts
FROM sn_logs.vpc_flow_logs
WHERE action = 'REJECT' AND dstport IN (22, 3389) AND "date" >= current_date - interval '1' day
GROUP BY srcaddr, dstport
ORDER BY attempts DESC
LIMIT 20;
```

**4. Top talkers by volume**

```sql
SELECT srcaddr, dstaddr, sum(bytes) AS total_bytes
FROM sn_logs.vpc_flow_logs
WHERE "date" >= current_date - interval '1' day
GROUP BY srcaddr, dstaddr
ORDER BY total_bytes DESC
LIMIT 20;
```

**5. Private server trying to reach the internet (egress that should not exist)**

```sql
SELECT from_unixtime(start) AS ts, dstaddr, dstport, action
FROM sn_logs.vpc_flow_logs
WHERE srcaddr = 'APP_IP' AND dstaddr NOT LIKE '10.%' AND "date" >= current_date - interval '1' day
ORDER BY start;
```

**6. Everything one suspect address did**

```sql
SELECT from_unixtime(start) AS ts, srcaddr, dstaddr, srcport, dstport, protocol, action, bytes
FROM sn_logs.vpc_flow_logs
WHERE srcaddr = 'APP_IP' OR dstaddr = 'APP_IP'
ORDER BY start;
```

**7. Traffic that arrived through the tunnel**

```sql
SELECT from_unixtime(start) AS ts, srcaddr, dstaddr, dstport, action
FROM sn_logs.vpc_flow_logs
WHERE srcaddr = 'GATEWAY_IP' AND dstaddr = 'APP_IP' AND dstport = 80
ORDER BY start DESC
LIMIT 50;
```

## Detection use cases

| Use case | Signal | Source | Response |
|---|---|---|---|
| Port scan from a compromised host | One source rejected on more than five ports | Query 2 | Isolate the instance, preserve evidence |
| Outbound call-home | Rejected or unexpected egress from the private tier | Query 5 | Isolate, review what the process was |
| Management port probing | Repeated rejects on 22 or 3389 | Query 3 | Confirm no port is open, tighten rules |
| Data exfiltration | A pair with unusually large byte totals | Query 4 | Identify the process, block the destination |
| Application outage or tampering | `UnHealthyHostCount` above 0 | CloudWatch alarm and SNS email | Check the instance, fail over |
| Web attack | `BlockedRequests` rising | WAF metric on the dashboard | Review sampled requests, tune rules |
| Unexpected tunnel use | Gateway to app flows at odd times | Query 7 | Review the peer, rotate keys |
| Deep inspection | Packets of a suspect flow | Traffic Mirroring on `sn-monitor` | Capture with `tcpdump`, analyse offline |

## Incident response runbook

Scenario: `sn-app-a` is scanning internal addresses and trying to reach the internet.

**1. Prepare (before anything happens)**
- An empty security group `sn-isolation-sg` exists: no inbound and no outbound rules.
- Flow Logs are on, the CloudWatch alarm and SNS email work, and the instance role allows Session Manager.

**2. Detect**
- Run query 2. One source address with more than five rejected ports is the lead.
- Run query 6 on that address to see the full timeline. Note the first and last timestamps.

**3. Contain**
- Replace the instance's security group with `sn-isolation-sg`. Tag it `IncidentStatus=ISOLATED`.
- A security group swap stops new connections. Connections already tracked can continue until they idle out. To cut those immediately as well, add a deny rule for the instance address at the top of the subnet's network ACL, then remove it after recovery.
- Do not terminate or stop the instance yet. Memory and running processes are still evidence.

**4. Preserve evidence** (see the notes below). Snapshot the volume before any change that touches the disk.

**5. Eradicate and recover**
- Launch a clean replacement from a known-good image, attach the normal security group, register it with the target group, deregister the isolated instance.
- Confirm the target is `Healthy` and the site answers.
- Terminate the compromised instance only after the snapshot is `Completed`.
- Rotate anything the instance could read: here, the database password in Parameter Store.

**6. Lessons learned**
- Why it was detectable: private tier with no egress turned the call-home into a visible reject.
- What would have caught it sooner: a GuardDuty finding, a CloudWatch alarm on the Flow Log reject count.
- Update the runbook and the rules, then rerun the drill.

## Evidence collection notes

| Item | How | Why |
|---|---|---|
| Volume snapshot | EC2, Volumes, create snapshot, tag `IncidentStatus=EVIDENCE`, description `IR sn-app-a` | Disk state at the time of isolation, restorable to a forensic instance |
| Console system log | EC2, Monitor and troubleshoot, Get system log, saved as `system-log.txt` | Boot and kernel messages, what the instance printed |
| Flow log records | Query 6 for the instance address, export the Athena result | Network timeline |
| Instance metadata | Instance ID, AMI, subnet, security groups before and after, launch time | Scope of the incident |
| Change history | CloudTrail event history shows who changed the security group and when | Proves the containment steps |
| Timeline | Written notes with UTC timestamps: detection, isolation, snapshot complete, recovery | Chain of events for the report |

Record who collected each item and when. Keep the snapshot and logs until the review is finished, then delete them to stop the cost.
