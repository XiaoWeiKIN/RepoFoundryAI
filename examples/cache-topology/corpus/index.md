# Cache topology research

## Decision to enable

Choose a cache topology for the tenant settings read path. The decision must
reduce database load and request latency without violating tenant isolation or
the accepted 30-second staleness budget.

## Research questions

- RQ-001: Which layer currently dominates request latency?
- RQ-002: Which topology meets the latency and database-load targets?
- RQ-003: Which invalidation and isolation constraints must enter the ADR?

## Decision drivers

- Read-path p95 below 60 ms at 1,200 requests per second.
- At least 60% fewer database reads.
- No cross-tenant cache-key collision.
- No value older than 30 seconds during normal operation.
- A configuration switch can disable each cache layer independently.

## Reading route

1. [Current state](./current-state.md)
2. [Options](./options.md)
3. [Benchmark](./benchmark.md)
