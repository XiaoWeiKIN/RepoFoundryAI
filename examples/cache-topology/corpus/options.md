# Cache topology options

The measured results are in [Benchmark](./benchmark.md). All options retain the
database as the source of truth.

## Option A: process-local L1 only

Each API replica stores settings in memory for five seconds.

- Lowest steady-state read latency.
- No new network dependency.
- Every replica warms independently.
- Invalidation is inconsistent across replicas unless a broadcast channel is
  added.

## Option B: shared Redis L2 only

Every cacheable read checks Redis before the database.

- One shared value and one invalidation target.
- Predictable behavior across replicas.
- Adds a network hop and Redis operational dependency to every cache hit.

## Option C: process-local L1 plus shared Redis L2

Each replica uses a five-second L1. L1 misses read a 30-second Redis entry;
Redis misses read the database and populate both layers.

- Meets latency and database-load targets.
- Redis absorbs cold starts and replica churn.
- Short L1 TTL bounds inconsistency if broadcast invalidation is delayed.
- Two layers increase implementation, observability and incident-debugging
  complexity.

## Ranking

Option C ranks first when tenant-safe keys, independent kill switches and
cache-age metrics are mandatory. Option A is faster in the benchmark but does
not provide a credible cross-replica invalidation contract. Option B is
acceptable when implementation simplicity matters more than the extra network
hop.
