BEGIN;

ALTER TABLE knowledge_articles
    ADD COLUMN IF NOT EXISTS embedding vector;
ALTER TABLE knowledge_articles
    ADD COLUMN IF NOT EXISTS embedding_model TEXT;
ALTER TABLE knowledge_articles
    ADD COLUMN IF NOT EXISTS embedding_dimensions INTEGER;
ALTER TABLE knowledge_articles
    ADD COLUMN IF NOT EXISTS embedded_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_knowledge_articles_fts
    ON knowledge_articles
    USING GIN (to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(content, '')));

CREATE INDEX IF NOT EXISTS idx_document_chunks_fts
    ON document_chunks
    USING GIN (to_tsvector('simple', coalesce(content, '')));

INSERT INTO schema_migrations (version)
VALUES ('0002_v03_hybrid_retrieval')
ON CONFLICT (version) DO NOTHING;

COMMIT;
