-- COMPELEC ONE Pfarrbüro-KI V2.0 – Enterprise Core
-- PostgreSQL 15+; additive initial migration for the existing V1.3 project line.
-- Apply as a migration owner. Runtime roles must not own these tables.
BEGIN;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS parish_tenants (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 tenant_key text NOT NULL UNIQUE,
 display_name text NOT NULL,
 status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended','archived')),
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS parish_org_units (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 tenant_id uuid NOT NULL REFERENCES parish_tenants(id) ON DELETE RESTRICT,
 parent_id uuid NULL,
 unit_type text NOT NULL CHECK (unit_type IN ('diocese','pastoral_region','parish','parish_office')),
 unit_key text NOT NULL,
 display_name text NOT NULL,
 status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive','archived')),
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT uq_parish_org_unit_key UNIQUE (tenant_id,unit_key),
 CONSTRAINT uq_parish_org_unit_tenant_id UNIQUE (tenant_id,id),
 CONSTRAINT fk_parish_org_parent_same_tenant FOREIGN KEY (tenant_id,parent_id)
  REFERENCES parish_org_units(tenant_id,id) ON DELETE RESTRICT,
 CONSTRAINT ck_parish_org_not_self_parent CHECK (parent_id IS NULL OR parent_id <> id)
);
CREATE INDEX IF NOT EXISTS ix_parish_org_parent ON parish_org_units(tenant_id,parent_id);

-- User identities are tenant-local in V2.0. A person working for multiple
-- dioceses receives a separate membership identity per tenant until federation is implemented.
CREATE TABLE IF NOT EXISTS parish_users (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 tenant_id uuid NOT NULL REFERENCES parish_tenants(id) ON DELETE RESTRICT,
 email text NOT NULL,
 display_name text NOT NULL,
 identity_subject text NULL,
 status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled','invited')),
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT uq_parish_user_tenant_id UNIQUE (tenant_id,id),
 CONSTRAINT uq_parish_user_email UNIQUE (tenant_id,email)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_parish_user_identity_subject
 ON parish_users(tenant_id,identity_subject) WHERE identity_subject IS NOT NULL;

CREATE TABLE IF NOT EXISTS parish_roles (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 role_key text NOT NULL UNIQUE,
 display_name text NOT NULL,
 description text NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS parish_permissions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 permission_key text NOT NULL UNIQUE,
 description text NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS parish_role_permissions (
 role_id uuid NOT NULL REFERENCES parish_roles(id) ON DELETE CASCADE,
 permission_id uuid NOT NULL REFERENCES parish_permissions(id) ON DELETE CASCADE,
 PRIMARY KEY(role_id,permission_id)
);

CREATE TABLE IF NOT EXISTS parish_memberships (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 tenant_id uuid NOT NULL REFERENCES parish_tenants(id) ON DELETE RESTRICT,
 user_id uuid NOT NULL,
 org_unit_id uuid NOT NULL,
 role_id uuid NOT NULL REFERENCES parish_roles(id) ON DELETE RESTRICT,
 status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked')),
 created_at timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT fk_parish_membership_user_same_tenant FOREIGN KEY (tenant_id,user_id)
  REFERENCES parish_users(tenant_id,id) ON DELETE RESTRICT,
 CONSTRAINT fk_parish_membership_org_same_tenant FOREIGN KEY (tenant_id,org_unit_id)
  REFERENCES parish_org_units(tenant_id,id) ON DELETE RESTRICT,
 CONSTRAINT uq_parish_membership UNIQUE(tenant_id,user_id,org_unit_id,role_id)
);
CREATE INDEX IF NOT EXISTS ix_parish_membership_user ON parish_memberships(tenant_id,user_id,status);

CREATE TABLE IF NOT EXISTS parish_cases (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 tenant_id uuid NOT NULL REFERENCES parish_tenants(id) ON DELETE RESTRICT,
 org_unit_id uuid NOT NULL,
 case_number bigint GENERATED ALWAYS AS IDENTITY,
 case_type text NOT NULL,
 subject text NOT NULL,
 description text NOT NULL DEFAULT '',
 status text NOT NULL DEFAULT 'open'
  CHECK (status IN ('open','in_progress','waiting','review','closed','archived')),
 priority text NOT NULL DEFAULT 'normal' CHECK (priority IN ('low','normal','high','urgent')),
 confidentiality text NOT NULL DEFAULT 'internal'
  CHECK (confidentiality IN ('public','internal','confidential','pastoral_secret')),
 assigned_user_id uuid NULL,
 due_at timestamptz NULL,
 created_by uuid NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT fk_parish_case_org_same_tenant FOREIGN KEY (tenant_id,org_unit_id)
  REFERENCES parish_org_units(tenant_id,id) ON DELETE RESTRICT,
 CONSTRAINT fk_parish_case_assignee_same_tenant FOREIGN KEY (tenant_id,assigned_user_id)
  REFERENCES parish_users(tenant_id,id) ON DELETE RESTRICT,
 CONSTRAINT fk_parish_case_creator_same_tenant FOREIGN KEY (tenant_id,created_by)
  REFERENCES parish_users(tenant_id,id) ON DELETE RESTRICT,
 CONSTRAINT uq_parish_case_tenant_id UNIQUE(tenant_id,id),
 CONSTRAINT uq_parish_case_number UNIQUE(tenant_id,case_number)
);
CREATE INDEX IF NOT EXISTS ix_parish_cases_queue ON parish_cases(tenant_id,org_unit_id,status,updated_at DESC);
CREATE INDEX IF NOT EXISTS ix_parish_cases_due ON parish_cases(tenant_id,due_at) WHERE due_at IS NOT NULL;

CREATE TABLE IF NOT EXISTS parish_documents (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 tenant_id uuid NOT NULL REFERENCES parish_tenants(id) ON DELETE RESTRICT,
 org_unit_id uuid NOT NULL,
 case_id uuid NULL,
 file_name text NOT NULL,
 media_type text NOT NULL,
 storage_key text NOT NULL,
 sha256 char(64) NOT NULL,
 classification text NOT NULL DEFAULT 'internal'
  CHECK (classification IN ('public','internal','confidential','pastoral_secret')),
 approval_status text NOT NULL DEFAULT 'draft'
  CHECK (approval_status IN ('draft','approved','rejected','archived')),
 uploaded_by uuid NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT fk_parish_document_org_same_tenant FOREIGN KEY (tenant_id,org_unit_id)
  REFERENCES parish_org_units(tenant_id,id) ON DELETE RESTRICT,
 CONSTRAINT fk_parish_document_case_same_tenant FOREIGN KEY (tenant_id,case_id)
  REFERENCES parish_cases(tenant_id,id) ON DELETE RESTRICT,
 CONSTRAINT fk_parish_document_uploader_same_tenant FOREIGN KEY (tenant_id,uploaded_by)
  REFERENCES parish_users(tenant_id,id) ON DELETE RESTRICT,
 CONSTRAINT uq_parish_document_hash UNIQUE(tenant_id,org_unit_id,sha256)
);

CREATE TABLE IF NOT EXISTS parish_audit_events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 tenant_id uuid NOT NULL REFERENCES parish_tenants(id) ON DELETE RESTRICT,
 actor_user_id uuid NULL,
 org_unit_id uuid NULL,
 event_type text NOT NULL,
 entity_type text NOT NULL,
 entity_id text NOT NULL,
 outcome text NOT NULL DEFAULT 'success' CHECK (outcome IN ('success','denied','failure')),
 correlation_id uuid NULL,
 metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
 occurred_at timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT fk_parish_audit_actor_same_tenant FOREIGN KEY (tenant_id,actor_user_id)
  REFERENCES parish_users(tenant_id,id) ON DELETE RESTRICT,
 CONSTRAINT fk_parish_audit_org_same_tenant FOREIGN KEY (tenant_id,org_unit_id)
  REFERENCES parish_org_units(tenant_id,id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS ix_parish_audit_timeline ON parish_audit_events(tenant_id,occurred_at DESC);
CREATE INDEX IF NOT EXISTS ix_parish_audit_entity ON parish_audit_events(tenant_id,entity_type,entity_id);

INSERT INTO parish_roles(role_key,display_name,description) VALUES
 ('bistum_admin','Bistumsadministration','Verwaltung innerhalb des eigenen Bistumsmandanten'),
 ('pastoralraum_admin','Administration Pastoraler Raum','Verwaltung des zugewiesenen Pastoralen Raums'),
 ('pfarrbuero','Pfarrbüro','Bearbeitung freigegebener Pfarrbüro-Vorgänge'),
 ('seelsorge','Seelsorge','Zugriff auf ausdrücklich freigegebene seelsorgliche Vorgänge'),
 ('ehrenamt','Ehrenamt','Verwaltung von Ehrenamtsaufgaben'),
 ('read_only','Lesender Zugriff','Lesender Zugriff im zugewiesenen Organisationsbereich')
ON CONFLICT(role_key) DO NOTHING;

INSERT INTO parish_permissions(permission_key,description) VALUES
 ('tenant.read','Mandanteninformationen lesen'),('tenant.admin','Mandantenkonfiguration verwalten'),
 ('org.read','Organisationseinheiten lesen'),('org.admin','Organisationseinheiten verwalten'),
 ('user.admin','Benutzer und Mitgliedschaften verwalten'),('case.read','Vorgänge lesen'),
 ('case.create','Vorgänge anlegen'),('case.update','Vorgänge bearbeiten'),('case.assign','Vorgänge zuweisen'),
 ('document.read','Dokumente lesen'),('document.upload','Dokumente hochladen'),
 ('document.approve','Dokumente freigeben'),('audit.read','Audit-Ereignisse lesen'),
 ('pastoral_secret.read','Besonders geschützte Seelsorgevorgänge lesen')
ON CONFLICT(permission_key) DO NOTHING;

-- Default least-privilege permission map. Pastoral-secret access is deliberately
-- not inherited by general administrators or Pfarrbüro roles.
WITH grants(role_key, permission_key) AS (
 VALUES
 ('bistum_admin','tenant.read'),('bistum_admin','tenant.admin'),
 ('bistum_admin','org.read'),('bistum_admin','org.admin'),('bistum_admin','user.admin'),
 ('bistum_admin','case.read'),('bistum_admin','case.create'),('bistum_admin','case.update'),('bistum_admin','case.assign'),
 ('bistum_admin','document.read'),('bistum_admin','document.upload'),('bistum_admin','document.approve'),('bistum_admin','audit.read'),
 ('pastoralraum_admin','org.read'),('pastoralraum_admin','user.admin'),
 ('pastoralraum_admin','case.read'),('pastoralraum_admin','case.create'),('pastoralraum_admin','case.update'),('pastoralraum_admin','case.assign'),
 ('pastoralraum_admin','document.read'),('pastoralraum_admin','document.upload'),('pastoralraum_admin','audit.read'),
 ('pfarrbuero','org.read'),('pfarrbuero','case.read'),('pfarrbuero','case.create'),('pfarrbuero','case.update'),
 ('pfarrbuero','document.read'),('pfarrbuero','document.upload'),
 ('seelsorge','org.read'),('seelsorge','case.read'),('seelsorge','case.create'),('seelsorge','case.update'),('seelsorge','pastoral_secret.read'),
 ('ehrenamt','org.read'),('ehrenamt','case.read'),('ehrenamt','case.create'),('ehrenamt','case.update'),
 ('read_only','org.read'),('read_only','case.read'),('read_only','document.read')
)
INSERT INTO parish_role_permissions(role_id,permission_id)
SELECT r.id,p.id
FROM grants g
JOIN parish_roles r ON r.role_key=g.role_key
JOIN parish_permissions p ON p.permission_key=g.permission_key
ON CONFLICT(role_id,permission_id) DO NOTHING;

-- Tenant table uses its own primary key as the session tenant identifier.
ALTER TABLE parish_tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE parish_tenants FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON parish_tenants;
CREATE POLICY tenant_isolation ON parish_tenants
 USING (id = nullif(current_setting('app.tenant_id',true),'')::uuid)
 WITH CHECK (id = nullif(current_setting('app.tenant_id',true),'')::uuid);

-- Tenant-scoped tables. Runtime sets app.tenant_id with SET LOCAL per transaction.
DO $$
DECLARE table_name text;
BEGIN
 FOREACH table_name IN ARRAY ARRAY['parish_org_units','parish_users','parish_memberships','parish_cases','parish_documents','parish_audit_events']
 LOOP
  EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',table_name);
  EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',table_name);
  EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON %I',table_name);
  EXECUTE format(
   'CREATE POLICY tenant_isolation ON %I USING (tenant_id = nullif(current_setting(''app.tenant_id'',true),'''')::uuid) WITH CHECK (tenant_id = nullif(current_setting(''app.tenant_id'',true),'''')::uuid)',
   table_name
  );
 END LOOP;
END $$;
COMMIT;
