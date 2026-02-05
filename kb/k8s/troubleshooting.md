# Kubernetes Troubleshooting Notes (Curated)

## Pod CrashLoopBackOff
- Check recent deploys, container exit codes, and liveness probes
- Common causes: bad config, missing secrets, out-of-memory

## DiskPressure
- Evicted pods often indicate disk pressure
- Clean unused images and rotate logs

## DNS Issues
- NXDOMAIN or slow lookups often point to CoreDNS or upstream resolver issues
- Restart CoreDNS as a safe first step

## Service Unreachable
- Validate endpoints and service selectors
- Check network policies and readiness probes

## Memory OOM
- Validate container limits vs real workload usage
- Track memory leaks across releases
