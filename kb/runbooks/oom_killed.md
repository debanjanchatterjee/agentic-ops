# Runbook: Pod OOMKilled

## Symptoms
- Pod restarts frequently
- Logs show "OOMKilled" or "out of memory"

## Likely Root Cause
- Container memory limit too low for workload spikes

## Safe Actions
- Increase memory limit/requests for the deployment
- Check memory leak in recent release

## Verification
- Observe stable RSS after restart
- No further OOM events for 30 minutes
