# ADR-005: PostgreSQL is the source of truth; vector, graph and search stores are derived

- **Status:** Accepted
- **Date:** 2026-11-03

## Context

§3.6 asks for relational, vector, graph and search infrastructure. If several stores each hold the "same" enrichment, it becomes unclear which copy is correct after a reviewer edits something.

The enrichment data is relational at heart: books, revisions, anchors, units, facts, entities, relationships, and review decisions with an audit trail. Search, semantic retrieval and graph traversal are read patterns over that data.

The MVP must run without servers.

## Decision

- **Production:** PostgreSQL (with JSONB for genre-specific payloads) is the **only write target** and the source of truth. Qdrant (vectors), Neo4j (graph) and OpenSearch (search) are **projections**. Sync jobs rebuild them from Postgres using an outbox table and idempotent upserts. Losing a projection is an inconvenience, not data loss.
- **Start lean:** vectors start in `pgvector` inside Postgres. They move to Qdrant when the corpus outgrows what pgvector serves well. The documented trigger is more than 10M vectors, or p95 latency above target.
- **MVP:** JSON files in `output/<pub_ref>/` plus `enrichment.db` (SQLite with the same table design). `search_index.json` is a derived lexical index and `graph.html` is a derived visualization.
- Original files go to object storage: MinIO/S3 with object lock in production, `store/originals/` in the MVP.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. Postgres as source of truth + derived stores (chosen)** | One truth; transactions; audit trail; projections can be rebuilt | Sync jobs needed |
| B. Neo4j as the main store | Natural fit for relations | Weak for audit and review workflows and for bulk relational queries; JSON payloads awkward |
| C. Vector DB only (RAG style) | Simple semantic search | Cannot reliably hold structured facts, review state or provenance |
| D. Document DB (MongoDB) | Flexible JSON | Weaker constraints and joins for anchors and reviews; still needs graph and search stores |
| E. Pipeline writes to every store directly | No sync layer | Dual-write inconsistency; partial failures leave the stores disagreeing |

## Consequences

- **+** Review edits happen in one place, and the projections follow.
- **+** The MVP SQLite schema mirrors Postgres, so migration is mostly a dialect change.
- **−** Search and graph lag slightly behind writes (eventual consistency, seconds).
- **−** Projection sync code must be idempotent and tested.

## Compliance / how verified

- MVP test: delete `search_index.json` and `graph.html`, run `ilm-engine rebuild-derived`, and get identical files rebuilt from `enrichment.db`.
- DDL for SQLite (MVP) and a Postgres sketch (production) are in [03-data-contracts.md](../03-data-contracts.md).

## Related

ADR-001, ADR-011, ADR-018; E11 storage tickets; E16 production backlog.
