-- Integrationstest für Mandantentrennung (ausschließlich Testdaten)
\set ON_ERROR_STOP on

INSERT INTO tenants (tenant_code, name) VALUES
  ('TEST-A', 'Testmandant A'),
  ('TEST-B', 'Testmandant B');

INSERT INTO customers (tenant_id, customer_no, company_name)
SELECT id, 'K-001', 'Beispielkunde ' || tenant_code
FROM tenants
WHERE tenant_code IN ('TEST-A', 'TEST-B');

-- Mandanten-IDs als Testparameter ermitteln, solange der DB-Administrator aktiv ist.
SELECT id AS tenant_a_id FROM tenants WHERE tenant_code = 'TEST-A' \gset
SELECT id AS tenant_b_id FROM tenants WHERE tenant_code = 'TEST-B' \gset

-- Laufzeitrolle ist weder Tabellen-Owner noch BYPASSRLS.
CREATE ROLE compelec_app_test LOGIN PASSWORD 'ci-only-test-password' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
GRANT USAGE ON SCHEMA public TO compelec_app_test;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO compelec_app_test;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO compelec_app_test;

SET ROLE compelec_app_test;
SELECT set_config('app.tenant_id', :'tenant_a_id', false);

DO $$
DECLARE
    visible_tenants INTEGER;
    visible_customers INTEGER;
    affected INTEGER;
BEGIN
    SELECT count(*) INTO visible_tenants FROM tenants;
    IF visible_tenants <> 1 THEN
        RAISE EXCEPTION 'RLS-Fehler: Erwartet 1 sichtbaren Mandanten, gefunden %', visible_tenants;
    END IF;

    SELECT count(*) INTO visible_customers FROM customers;
    IF visible_customers <> 1 THEN
        RAISE EXCEPTION 'RLS-Fehler: Erwartet 1 sichtbaren Kunden, gefunden %', visible_customers;
    END IF;

    -- Der explizite Mandantenfilter B darf unter Tenant-A-Kontext keine Zeile ändern.
    UPDATE customers
       SET company_name = 'UNZULAESSIGER CROSS-TENANT-ZUGRIFF'
     WHERE company_name = 'Beispielkunde TEST-B';
    GET DIAGNOSTICS affected = ROW_COUNT;
    IF affected <> 0 THEN
        RAISE EXCEPTION 'RLS-Fehler: Mandantenfremde Zeilen wurden verändert';
    END IF;
END $$;

RESET ROLE;
DROP OWNED BY compelec_app_test;
DROP ROLE compelec_app_test;
\echo 'RLS-Mandantentrennung erfolgreich geprüft.'
