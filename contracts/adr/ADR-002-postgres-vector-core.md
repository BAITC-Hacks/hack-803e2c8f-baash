# ADR 002 PostgreSQL Vector Core

Status: accepted with a benchmark gate

## Decision

Use PostgreSQL for operational state and audit metadata, PostGIS for spatial queries and pgvector HNSW for the first retrieval index. Store recordings, media, exports and immutable raw files in S3-compatible object storage.

## Reasons

- A single transactional core reduces operational complexity and allows region, status and service filters to run with vector retrieval.
- The available data volume is compatible with a benchmarkable PostgreSQL baseline.
- The team can introduce a dedicated vector engine later without changing the retrieval API.

## Extraction gate

Move vectors to a dedicated engine only when a reproducible test on representative filters shows that PostgreSQL cannot meet the agreed p95 latency, recall and ingestion SLO at the required data size. The benchmark must include index build time, backup, restore, access control and operating effort.

