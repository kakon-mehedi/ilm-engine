-- enrichment.db (MVP), 03-data-contracts §19. Same tables and columns as the PostgreSQL design
-- (§20, T-161). The block table stores hashes, never text: text is resolved from the read-only
-- original through anchors (ADR-001).
CREATE TABLE IF NOT EXISTS book (pub_ref TEXT PRIMARY KEY, pub_id TEXT NOT NULL, revision INTEGER NOT NULL,
  source_code TEXT, schema_version TEXT, adapter TEXT, canonical_content_hash TEXT NOT NULL,
  source_declared_hash TEXT, source_declared_hash_verified INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS block (block_id TEXT, pub_ref TEXT, ord INTEGER, page INTEGER, scan_page INTEGER,
  kind TEXT, origin TEXT, block_hash TEXT NOT NULL, PRIMARY KEY (pub_ref, block_id));
CREATE TABLE IF NOT EXISTS section (section_id TEXT PRIMARY KEY, pub_ref TEXT, parent_id TEXT, level INTEGER,
  title TEXT, heading_block_id TEXT, start_block_id TEXT, end_block_id TEXT, origin TEXT, data JSON);
CREATE TABLE IF NOT EXISTS anchor (anchor_id TEXT PRIMARY KEY, owner_kind TEXT, owner_id TEXT, pub_ref TEXT,
  block_id TEXT, start INTEGER, "end" INTEGER, quote TEXT, block_hash TEXT, status TEXT DEFAULT 'valid');
CREATE INDEX IF NOT EXISTS anchor_owner ON anchor(owner_kind, owner_id);
CREATE INDEX IF NOT EXISTS anchor_block ON anchor(pub_ref, block_id);
CREATE TABLE IF NOT EXISTS annotation (annotation_id TEXT PRIMARY KEY, pub_ref TEXT, type TEXT, source_block_id TEXT,
  target_block_ids JSON, link_method TEXT, status TEXT, data JSON);
CREATE TABLE IF NOT EXISTS citation (citation_id TEXT PRIMARY KEY, pub_ref TEXT, title_normalized TEXT, work_id TEXT,
  data JSON);
CREATE TABLE IF NOT EXISTS work (work_id TEXT PRIMARY KEY, title TEXT, title_normalized TEXT, status TEXT, data JSON);
CREATE TABLE IF NOT EXISTS work_relation (relation_id TEXT PRIMARY KEY, type TEXT, subject_work_id TEXT,
  object_work_id TEXT, origin TEXT, assertion TEXT, confidence REAL, review_status TEXT, data JSON);
CREATE TABLE IF NOT EXISTS knowledge_unit (unit_id TEXT PRIMARY KEY, pub_ref TEXT, genre TEXT, unit_type TEXT,
  entry_no INTEGER, section_id TEXT, subject_entity_id TEXT, origin TEXT, confidence REAL, review_status TEXT,
  payload JSON);
CREATE TABLE IF NOT EXISTS fact (fact_id TEXT PRIMARY KEY, unit_id TEXT REFERENCES knowledge_unit, predicate TEXT,
  object JSON, origin TEXT, assertion TEXT, confidence REAL, sensitive JSON, review_status TEXT, provenance JSON);
CREATE TABLE IF NOT EXISTS entity (entity_id TEXT PRIMARY KEY, entity_type TEXT, canonical_name TEXT,
  canonical_name_normalized TEXT, gender TEXT, disambiguation TEXT, confidence REAL, review_status TEXT, data JSON);
CREATE TABLE IF NOT EXISTS relationship (relation_id TEXT PRIMARY KEY, type TEXT, subject_entity_id TEXT,
  object_entity_id TEXT, attrs JSON, origin TEXT, assertion TEXT, confidence REAL, review_status TEXT,
  provenance JSON);
CREATE TABLE IF NOT EXISTS issue (issue_id TEXT PRIMARY KEY, code TEXT, severity TEXT, target_kind TEXT,
  target_id TEXT, data JSON);
CREATE TABLE IF NOT EXISTS validation (target_kind TEXT, target_id TEXT, confidence REAL, decision TEXT, data JSON,
  PRIMARY KEY (target_kind, target_id));
CREATE TABLE IF NOT EXISTS review_item (review_id TEXT PRIMARY KEY, target_kind TEXT, target_id TEXT,
  priority INTEGER, required_role TEXT, status TEXT, data JSON);
CREATE TABLE IF NOT EXISTS review_audit (review_id TEXT, decided_at TEXT, reviewer_id TEXT, reviewer_role TEXT,
  decision TEXT, old_value JSON, new_value JSON, reason TEXT);
CREATE TABLE IF NOT EXISTS run (run_id TEXT PRIMARY KEY, pub_ref TEXT, manifest JSON);
