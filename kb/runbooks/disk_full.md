# Runbook: Node Disk Full

## Symptoms
- Pods fail to start with "no space left on device"
- Node reports DiskPressure

## Likely Root Cause
- Log accumulation or container image bloat

## Safe Actions
- Clear old logs and unused images
- Increase disk size if needed

## Verification
- Disk usage under 80%
- Pods schedule successfully
