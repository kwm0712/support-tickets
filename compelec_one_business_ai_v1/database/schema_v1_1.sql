-- COMPELEC ONE – Business AI
-- PostgreSQL-Grundschema V1.1 – Entwurf, noch nicht produktiv auszuführen.
-- Mandantentrennung wird zusätzlich durch Row-Level Security abgesichert.
-- Die Anwendung muss app.tenant_id pro Datenbankverbindung/transaktion setzen.

CREATE TABLE tenants (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE app_users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id BIGINT NOT NULL REFERENCES tenants(id),
    email TEXT NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'leitung', 'support', 'vertrieb', 'telefon', 'mail', 'lesend')),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, id),
    UNIQUE (tenant_id, email)
);

CREATE TABLE customers (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id BIGINT NOT NULL REFERENCES tenants(id),
    customer_no TEXT NOT NULL,
    company_name TEXT NOT NULL,
    contact_name TEXT,
    email TEXT,
    phone TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, id),
    UNIQUE (tenant_id, customer_no)
);

-- Zentrale Kundenhistorie: Support, Vertrieb, Telefon und E-Mail laufen hier zusammen.
CREATE TABLE customer_interactions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id BIGINT NOT NULL REFERENCES tenants(id),
    customer_id BIGINT NOT NULL,
    channel TEXT NOT NULL CHECK (channel IN ('support', 'sales', 'phone', 'email', 'internal')),
    direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound', 'internal')),
    subject TEXT NOT NULL,
    body TEXT,
    created_by BIGINT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, id),
    FOREIGN KEY (tenant_id, customer_id) REFERENCES customers(tenant_id, id),
    FOREIGN KEY (tenant_id, created_by) REFERENCES app_users(tenant_id, id)
);

CREATE TABLE support_tickets (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id BIGINT NOT NULL REFERENCES tenants(id),
    customer_id BIGINT NOT NULL,
    interaction_id BIGINT,
    ticket_no TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'critical')),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'waiting', 'resolved', 'closed')),
    assigned_to BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, id),
    UNIQUE (tenant_id, ticket_no),
    FOREIGN KEY (tenant_id, customer_id) REFERENCES customers(tenant_id, id),
    FOREIGN KEY (tenant_id, interaction_id) REFERENCES customer_interactions(tenant_id, id),
    FOREIGN KEY (tenant_id, assigned_to) REFERENCES app_users(tenant_id, id)
);

CREATE TABLE phone_call_details (
    tenant_id BIGINT NOT NULL,
    interaction_id BIGINT NOT NULL,
    phone_number TEXT,
    callback_required BOOLEAN NOT NULL DEFAULT FALSE,
    callback_due_at TIMESTAMPTZ,
    assigned_to BIGINT,
    PRIMARY KEY (tenant_id, interaction_id),
    FOREIGN KEY (tenant_id, interaction_id) REFERENCES customer_interactions(tenant_id, id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id, assigned_to) REFERENCES app_users(tenant_id, id)
);

CREATE TABLE email_drafts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id BIGINT NOT NULL REFERENCES tenants(id),
    interaction_id BIGINT,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    approval_status TEXT NOT NULL DEFAULT 'draft' CHECK (approval_status IN ('draft', 'pending_approval', 'approved', 'rejected', 'sent')),
    created_by BIGINT,
    approved_by BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at TIMESTAMPTZ,
    UNIQUE (tenant_id, id),
    FOREIGN KEY (tenant_id, interaction_id) REFERENCES customer_interactions(tenant_id, id),
    FOREIGN KEY (tenant_id, created_by) REFERENCES app_users(tenant_id, id),
    FOREIGN KEY (tenant_id, approved_by) REFERENCES app_users(tenant_id, id)
);

CREATE TABLE audit_log (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id BIGINT NOT NULL REFERENCES tenants(id),
    actor_user_id BIGINT,
    entity_type TEXT NOT NULL,
    entity_id BIGINT,
    action TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id, actor_user_id) REFERENCES app_users(tenant_id, id)
);

CREATE INDEX idx_customers_tenant_name ON customers(tenant_id, company_name);
CREATE INDEX idx_interactions_customer_time ON customer_interactions(tenant_id, customer_id, occurred_at DESC);
CREATE INDEX idx_tickets_status_priority ON support_tickets(tenant_id, status, priority);
CREATE INDEX idx_tickets_assignee ON support_tickets(tenant_id, assigned_to);
CREATE INDEX idx_email_approval ON email_drafts(tenant_id, approval_status, created_at DESC);
CREATE INDEX idx_audit_entity_time ON audit_log(tenant_id, entity_type, entity_id, created_at DESC);

-- Fail-closed: Ohne gesetzten Mandantenkontext liefert RLS keine Mandantendaten.
ALTER TABLE app_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE phone_call_details ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_app_users ON app_users
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), '')::BIGINT)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), '')::BIGINT);
CREATE POLICY tenant_isolation_customers ON customers
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), '')::BIGINT)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), '')::BIGINT);
CREATE POLICY tenant_isolation_interactions ON customer_interactions
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), '')::BIGINT)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), '')::BIGINT);
CREATE POLICY tenant_isolation_tickets ON support_tickets
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), '')::BIGINT)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), '')::BIGINT);
CREATE POLICY tenant_isolation_calls ON phone_call_details
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), '')::BIGINT)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), '')::BIGINT);
CREATE POLICY tenant_isolation_emails ON email_drafts
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), '')::BIGINT)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), '')::BIGINT);
CREATE POLICY tenant_isolation_audit ON audit_log
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), '')::BIGINT)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), '')::BIGINT);
