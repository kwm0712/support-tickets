-- Executed against an empty PostgreSQL 16 CI database after applying the migration twice.
DO $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='pfarrbuero_runtime') THEN
  CREATE ROLE pfarrbuero_runtime LOGIN PASSWORD 'runtime-test-password' NOBYPASSRLS;
 END IF;
END $$;

INSERT INTO parish_tenants(id,tenant_key,display_name) VALUES
 ('10000000-0000-0000-0000-000000000001','tenant-a','Test Bistum A'),
 ('20000000-0000-0000-0000-000000000002','tenant-b','Test Bistum B')
ON CONFLICT (id) DO NOTHING;

INSERT INTO parish_org_units(id,tenant_id,parent_id,unit_type,unit_key,display_name) VALUES
 ('10000000-0000-0000-0000-000000000011','10000000-0000-0000-0000-000000000001',NULL,'diocese','a-root','Bistum A'),
 ('20000000-0000-0000-0000-000000000022','20000000-0000-0000-0000-000000000002',NULL,'diocese','b-root','Bistum B')
ON CONFLICT (id) DO NOTHING;

INSERT INTO parish_users(id,tenant_id,email,display_name) VALUES
 ('10000000-0000-0000-0000-000000000101','10000000-0000-0000-0000-000000000001','user-a@example.invalid','Test Benutzer A'),
 ('20000000-0000-0000-0000-000000000202','20000000-0000-0000-0000-000000000002','user-b@example.invalid','Test Benutzer B'),
 ('10000000-0000-0000-0000-000000000103','10000000-0000-0000-0000-000000000001','readonly-a@example.invalid','Lesender Testbenutzer A')
ON CONFLICT (id) DO NOTHING;

INSERT INTO parish_cases(tenant_id,org_unit_id,case_type,subject,created_by) VALUES
 ('10000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000011','Test','Testfall A','10000000-0000-0000-0000-000000000101'),
 ('20000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000022','Test','Testfall B – darf nicht sichtbar sein','20000000-0000-0000-0000-000000000202'),
 ('10000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000011','Seelsorge','Vertraulicher Seelsorgevorgang','10000000-0000-0000-0000-000000000101');

INSERT INTO parish_memberships(tenant_id,user_id,org_unit_id,role_id)
SELECT '10000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000101',
       '10000000-0000-0000-0000-000000000011',id
FROM parish_roles WHERE role_key='pfarrbuero'
ON CONFLICT DO NOTHING;
INSERT INTO parish_memberships(tenant_id,user_id,org_unit_id,role_id)
SELECT '10000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000103',
       '10000000-0000-0000-0000-000000000011',id
FROM parish_roles WHERE role_key='read_only'
ON CONFLICT DO NOTHING;
INSERT INTO parish_memberships(tenant_id,user_id,org_unit_id,role_id)
SELECT '20000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000202',
       '20000000-0000-0000-0000-000000000022',id
FROM parish_roles WHERE role_key='pfarrbuero'
ON CONFLICT DO NOTHING;

GRANT USAGE ON SCHEMA public TO pfarrbuero_runtime;
GRANT SELECT ON parish_tenants,parish_org_units,parish_users,parish_memberships TO pfarrbuero_runtime;
GRANT SELECT ON parish_roles,parish_role_permissions,parish_permissions TO pfarrbuero_runtime;
GRANT INSERT ON parish_org_units TO pfarrbuero_runtime;
GRANT SELECT,INSERT ON parish_cases,parish_audit_events TO pfarrbuero_runtime;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO pfarrbuero_runtime;

BEGIN;
SET LOCAL ROLE pfarrbuero_runtime;

-- Missing tenant context must fail closed.
DO $$
DECLARE missing_context_rows integer;
BEGIN
 SELECT count(*) INTO missing_context_rows FROM parish_cases;
 IF missing_context_rows <> 0 THEN
  RAISE EXCEPTION 'RLS failed closed without tenant context: expected 0 rows, got %',missing_context_rows;
 END IF;
END $$;

SELECT set_config('app.tenant_id','10000000-0000-0000-0000-000000000001',true);
DO $$
DECLARE visible_rows integer;
DECLARE case_rows integer;
DECLARE cross_tenant_write_blocked boolean := false;
BEGIN
 SELECT count(*) INTO visible_rows FROM parish_org_units;
 IF visible_rows <> 1 THEN
  RAISE EXCEPTION 'Tenant isolation failed: expected 1 visible org unit, got %',visible_rows;
 END IF;
 SELECT count(*) INTO case_rows FROM parish_cases;
 IF case_rows <> 2 THEN
  RAISE EXCEPTION 'Tenant case isolation failed: expected 2 cases, got %',case_rows;
 END IF;
 BEGIN
  INSERT INTO parish_org_units(id,tenant_id,parent_id,unit_type,unit_key,display_name)
  VALUES ('30000000-0000-0000-0000-000000000033',
          '20000000-0000-0000-0000-000000000002',NULL,'diocese','cross-tenant','Forbidden');
 EXCEPTION WHEN insufficient_privilege THEN
  cross_tenant_write_blocked := true;
 END;
 IF NOT cross_tenant_write_blocked THEN
  RAISE EXCEPTION 'Tenant isolation failed: cross-tenant write was not blocked';
 END IF;
END $$;
ROLLBACK;
