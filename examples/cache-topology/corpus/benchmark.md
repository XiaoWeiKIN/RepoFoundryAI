# Cache topology benchmark

## Method

Replay the same tenant-settings workload for 15 minutes against 10 API
replicas at 1,200 requests per second. Warm each candidate for two minutes.
Record read-path p95, database queries per second and cache behavior.

The dataset contains 20,000 tenants with a Zipf-like access distribution.
Writes remain fixed at four per second.

## Results

| Candidate | Read p95 | Database reads | Reduction | Material limitation |
|---|---:|---:|---:|---|
| No cache | 184 ms | 1,180 q/s | 0% | Misses both targets |
| L1 only | 29 ms | 330 q/s | 72% | Replica-local invalidation |
| Redis only | 58 ms | 420 q/s | 64% | Network hop on every hit |
| L1 + Redis | 34 ms | 342 q/s | 71% | Two-layer complexity |

## Interpretation

L1 plus Redis meets both quantitative targets and retains a shared cold-start
layer. L1 only has the best latency, but its invalidation weakness conflicts
with the cross-replica consistency requirement.

## Limitations

This benchmark does not simulate a regional Redis outage or an invalidation
backlog. Those cases must become ExecPlan acceptance tests. The numbers are
example data for demonstrating the workflow, not production sizing guidance.
