-- Executed against an empty PostgreSQL 16 CI database after applying the migration twice.
DO $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='pfarrbuero_runtime') THEN
  CREATE ROLE pfarrbuero_runtime NOLOGIN NOBYPASSRLS;
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

GRANT USAGE ON SCHEMA public TO pfarrbuero_runtime;
GRANT SELECT,INSERT ON parish_tenants,parish_org_units TO pfarrbuero_runtime;

BEGIN;
SET LOCAL ROLE pfarrbuero_runtime;
SELECT set_config('app.tenant_id','10000000-0000-0000-0000-000000000001',true);
DO $$
DECLARE visible_rows integer;
DECLARE cross_tenant_write_blocked boolean := false;
BEGIN
 SELECT count(*) INTO visible_rows FROM parish_org_units;
 IF visible_rows <> 1 THEN
  RAISE EXCEPTION 'Tenant isolation failed: expected 1 visible org unit, got %',visible_rows;
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
