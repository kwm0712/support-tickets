BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tenants (
    tenant_key TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    tenant_key TEXT NOT NULL REFERENCES tenants(tenant_key),
    username TEXT NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'agent', 'viewer')),
    password_salt TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_key, username)
);

CREATE TABLE IF NOT EXISTS tickets (
    id BIGSERIAL PRIMARY KEY,
    tenant_key TEXT NOT NULL REFERENCES tenants(tenant_key),
    ticket_no TEXT NOT NULL,
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    customer TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('Offen', 'In Bearbeitung', 'Gelöst')),
    priority TEXT NOT NULL CHECK (priority IN ('Hoch', 'Mittel', 'Niedrig')),
    assignee TEXT,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_key, ticket_no)
);

CREATE TABLE IF NOT EXISTS knowledge_articles (
    id BIGSERIAL PRIMARY KEY,
    tenant_key TEXT NOT NULL REFERENCES tenants(tenant_key),
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approval_status TEXT NOT NULL DEFAULT 'draft'
        CHECK (approval_status IN ('draft', 'approved', 'rejected')),
    privacy_level TEXT NOT NULL DEFAULT 'internal'
        CHECK (privacy_level IN ('public', 'internal', 'confidential'))
);

CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    tenant_key TEXT NOT NULL REFERENCES tenants(tenant_key),
    filename TEXT NOT NULL,
    category TEXT NOT NULL,
    source TEXT,
    file_type TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    approval_status TEXT NOT NULL DEFAULT 'draft'
        CHECK (approval_status IN ('draft', 'approved', 'rejected')),
    privacy_level TEXT NOT NULL DEFAULT 'internal'
        CHECK (privacy_level IN ('public', 'internal', 'confidential')),
    imported_by TEXT NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_by TEXT,
    reviewed_at TIMESTAMPTZ,
    UNIQUE (tenant_key, sha256)
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id BIGSERIAL PRIMARY KEY,
    tenant_key TEXT NOT NULL REFERENCES tenants(tenant_key),
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_no INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector,
    embedding_model TEXT,
    embedding_dimensions INTEGER,
    embedded_at TIMESTAMPTZ,
    UNIQUE (document_id, chunk_no)
);

CREATE TABLE IF NOT EXISTS assistant_runs (
    id BIGSERIAL PRIMARY KEY,
    tenant_key TEXT NOT NULL REFERENCES tenants(tenant_key),
    actor TEXT NOT NULL,
    provider TEXT NOT NULL,
    privacy_level TEXT NOT NULL
        CHECK (privacy_level IN ('public', 'internal', 'confidential')),
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    correlation_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS assistant_evidence (
    id BIGSERIAL PRIMARY KEY,
    tenant_key TEXT NOT NULL REFERENCES tenants(tenant_key),
    assistant_run_id BIGINT NOT NULL REFERENCES assistant_runs(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    source_id BIGINT NOT NULL,
    rank INTEGER NOT NULL,
    lexical_score DOUBLE PRECISION,
    vector_score DOUBLE PRECISION,
    combined_score DOUBLE PRECISION,
    UNIQUE (assistant_run_id, rank)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    tenant_key TEXT NOT NULL REFERENCES tenants(tenant_key),
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    correlation_id TEXT,
    details TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tickets_tenant_status
    ON tickets (tenant_key, status, priority);
CREATE INDEX IF NOT EXISTS idx_knowledge_tenant_governance
    ON knowledge_articles (tenant_key, approval_status, privacy_level);
CREATE INDEX IF NOT EXISTS idx_documents_tenant_governance
    ON documents (tenant_key, approval_status, privacy_level);
CREATE INDEX IF NOT EXISTS idx_chunks_tenant_document
    ON document_chunks (tenant_key, document_id);
CREATE INDEX IF NOT EXISTS idx_assistant_runs_tenant_created
    ON assistant_runs (tenant_key, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_tenant_created
    ON audit_log (tenant_key, created_at DESC);

INSERT INTO schema_migrations (version)
VALUES ('0001_v03_core')
ON CONFLICT (version) DO NOTHING;

COMMIT;
