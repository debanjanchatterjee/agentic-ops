# Runbook: Service Unavailable / 5xx

## Symptoms
- Alert: 5xx error rate spikes
- Logs show connection timeouts

## Likely Root Cause
- Deployment crash loop or downstream dependency outage

## Safe Actions
- Restart deployment
- Check dependency health and circuit breakers

## Verification
- 5xx rate returns to baseline
- Successful requests sustained for 15 minutes
