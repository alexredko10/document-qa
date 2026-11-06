# ADR-001: Vector Store Strategy — DynamoDB Native Vector Search vs S3 Vectors

**Status:** PROPOSED — benchmark and approval required  
**Date:** 2026-11-06  
**Decision owners:** Human project owner + architecture reviewer

## Context
The platform needs permission-aware semantic retrieval of approved, versioned document chunks. DynamoDB gained **native vector search in August 2026**, changing the previous assumption that vectors required a separate datastore. S3 Vectors is also available. We need a data-store decision based on measured retrieval, operation and security needs rather than platform fashion.

## Distinguish storage responsibilities
- **Normal S3 object buckets:** originals, approved immutable snapshots, extracted/chunk text payload and artifacts.
- **DynamoDB operational table(s):** OKF lifecycle, approval/version metadata, execution records, ACL/policy data, pointer-based audit metadata.
- **VectorStore backend (ONE preferred per active corpus):** *either* native DynamoDB vector index *or* S3 Vectors; keep adapter boundary. Duplicating vectors between both is an evaluation exercise or explicitly justified failover architecture, not default.
- **Embedding model:** Bedrock Titan Text Embeddings V2 (candidate). Chunking occurs in application ingestion, NOT in Titan.

## Options
### A — DynamoDB native vector index
**Pros:** vectors and related attributes can coexist; one service for metadata plus vectors; simple operational consistency; real-time use cases; native ANN with attribute filters.  
**Cons/questions:** vector-index billing for our access pattern, access-policy representation, item and index design, search schema, scalability/latency/recall for filtered corpora, whether embedding records should share business tables, schema evolution and API/region SDK support.  
**Important:** `SearchVectors` is a dedicated operation; do not pretend a normal DynamoDB Query/GSI is a vector search.

### B — Amazon S3 Vectors
**Pros:** purpose-built economical vector storage; potentially appropriate for large, lower-query-rate knowledge corpora; metadata-filtered similarity search; clean separation from operational records.  
**Cons/questions:** additional datastore and synchronisation/publication workflow, eventual exposure/revocation interactions, index configuration immutability for certain fields, query latency/recall under filters, operational cost versus DynamoDB.  
**Important:** normal S3 object buckets and S3 vector buckets are different resource types.

### C — Other vector backend
OpenSearch/pgvector/etc. are fallback candidates only if a documented requirement (hybrid lexical retrieval, flexible query semantics, recall/latency or operations) cannot be satisfied effectively by options A/B. They do not become dependencies by default.

## Proposed decision
**DEFER BACKEND CHOICE.** Implement and test a minimal `VectorStore` interface and run a controlled benchmark. Do not deploy both permanently unless objective evidence supports that complexity. Keep regular S3 for documents, DynamoDB for operational data independently from selected vector backend.

## Contract / abstraction
Required operations: upsert(index_version, chunk_id, vector, filterable_metadata), delete/revoke, query(vector, authorised_scope, top_k), and health/metrics; preserve provenance and explainability. Never trust user-supplied tenant/role filters. Authorisation is enforced server-side before query and verified against authoritative metadata after retrieval before supplying context. Metadata-based prefilter must not be the only security boundary.

## Benchmark acceptance criteria (set numerical thresholds before running)
- Same synthetic corpus, Titan embedding version/dimension, chunk policy, ACL distribution, request load, warm/cold profile and query dataset.
- Compare Recall@k, nDCG/MRR, P50/P95 retrieval latency, total cost at low/medium projected request volume, operational effort, ingestion/update/revocation latency, multi-role filtering safety, IAM blast radius.
- Record pricing assumptions, region, SDK versions, index settings, dataset size and raw measurements.
- Negative tests: finance->HR denied; revoked chunk cannot appear in model context; forged metadata does not grant authorisation; tenant boundaries enforced; reindex rollback.
- Cost at representative small pet-project scale is more important than headline hyperscale benchmarks.

## Consequences
A short-lived comparison implementation is acceptable, but the main application remains storage-agnostic. Benchmark result -> amend ADR status to ACCEPTED -> remove unchosen production path or retain as clearly labelled optional adapter. No code change merely because the ADR exists.

## References (checked 2026-11-06)
- https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-dynamodb-vector-search/
- https://aws.amazon.com/blogs/database/build-semantic-search-with-native-vector-support-in-amazon-dynamodb/
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-indexes.html
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-query.html
