BEGIN;

-- Enforce tenant isolation in PostgreSQL itself, not only in repository WHERE clauses.
-- The application role must not be a superuser or have BYPASSRLS.
DO $$
DECLARE
    table_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'tenants',
        'users',
        'tickets',
        'knowledge_articles',
        'documents',
        'document_chunks',
        'assistant_runs',
        'assistant_evidence',
        'audit_log'
    ]
    LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', table_name);
        EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON public.%I', table_name);
        EXECUTE format(
            'CREATE POLICY tenant_isolation ON public.%I
             USING (tenant_key = NULLIF(current_setting(''app.tenant_id'', true), ''''))
             WITH CHECK (tenant_key = NULLIF(current_setting(''app.tenant_id'', true), ''''))',
            table_name
        );
    END LOOP;
END
$$;

INSERT INTO schema_migrations (version)
VALUES ('0003_tenant_row_level_security')
ON CONFLICT (version) DO NOTHING;

COMMIT;
