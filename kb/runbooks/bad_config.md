# Runbook: Bad Config Rollback

## Symptoms
- Service degraded after config change
- Error logs indicate invalid or missing config

## Likely Root Cause
- Incorrect config values or format

## Safe Actions
- Roll back to last known good config
- Add validation checks in CI

## Verification
- Error rates normalize
- Config validation passes
