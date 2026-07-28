# Current state

## Observations

The example service runs 10 stateless API replicas. A load test at 1,200
requests per second produced:

| Metric | Baseline |
|---|---:|
| Read-path p50 | 72 ms |
| Read-path p95 | 184 ms |
| Database reads | 1,180 queries/s |
| Settings writes | 4 writes/s |

Tenant settings change infrequently. Product requirements permit a value to be
up to 30 seconds old during normal operation. Every lookup already carries a
stable `tenant_id`.

## Interpretation

Database reads dominate both latency and backend load. The read/write ratio
makes caching useful, while the 30-second staleness budget permits TTL-based
recovery if an invalidation message is delayed.

## Constraints

- Cache keys must include `tenant_id` and a cache schema version.
- A cache outage must fall back to the database.
- Operators must be able to disable L1 and L2 independently.
- Cache behavior needs hit-rate, age, fallback and invalidation-lag metrics.
