# Runbook: CPU Spike

## Symptoms
- CPU usage > 90% for 5+ minutes
- Latency increases

## Likely Root Cause
- Hot loop in code or traffic surge

## Safe Actions
- Scale deployment horizontally
- Enable autoscaling if disabled

## Verification
- CPU stabilizes < 70%
- Latency returns to baseline
