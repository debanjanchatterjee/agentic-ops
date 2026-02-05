# Runbook: DNS Resolution Failures

## Symptoms
- NXDOMAIN errors
- Services cannot reach dependencies by name

## Likely Root Cause
- Cluster DNS outage or stale cache

## Safe Actions
- Flush DNS cache on node or restart CoreDNS
- Verify upstream resolvers

## Verification
- DNS lookup success rate > 99%
- Service connectivity restored
