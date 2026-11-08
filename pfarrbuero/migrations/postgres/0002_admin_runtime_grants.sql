-- V2.0.3 administrative API runtime grants.
-- Apply only after the deployment has created its dedicated non-owner runtime role.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='pfarrbuero_runtime') THEN
    GRANT SELECT, INSERT ON parish_users TO pfarrbuero_runtime;
    GRANT SELECT, INSERT, UPDATE ON parish_memberships TO pfarrbuero_runtime;
    GRANT SELECT ON parish_roles, parish_role_permissions, parish_permissions TO pfarrbuero_runtime;
    GRANT SELECT, INSERT ON parish_org_units TO pfarrbuero_runtime;
    GRANT INSERT ON parish_audit_events TO pfarrbuero_runtime;
  END IF;
END $$;
