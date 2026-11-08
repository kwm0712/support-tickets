"""Tenant-scoped administration repository for Pfarrbüro-KI V2.0.3."""
from __future__ import annotations
from dataclasses import dataclass
from uuid import UUID, uuid4
import json
import psycopg
from psycopg.rows import dict_row

@dataclass(frozen=True)
class AdminConfig:
    dsn: str
    tenant_id: str
    org_unit_id: str
    actor_user_id: str

class AdminRepository:
    """Administration operations; writes and audit events share one transaction."""
    def __init__(self, config: AdminConfig):
        self.config = config
    def _connect(self):
        return psycopg.connect(self.config.dsn, row_factory=dict_row)
    def _set_context(self, conn):
        conn.execute("SELECT set_config('app.tenant_id', %s, true)", (self.config.tenant_id,))
    def _require(self, conn, permission):
        row = conn.execute("""
            WITH RECURSIVE scope(id,parent_id) AS (
              SELECT id,parent_id FROM parish_org_units WHERE id=%s AND tenant_id=%s
              UNION ALL SELECT p.id,p.parent_id FROM parish_org_units p
              JOIN scope c ON c.parent_id=p.id WHERE p.tenant_id=%s
            )
            SELECT EXISTS (
              SELECT 1 FROM parish_memberships m
              JOIN parish_roles r ON r.id=m.role_id
              JOIN parish_role_permissions rp ON rp.role_id=r.id
              JOIN parish_permissions p ON p.id=rp.permission_id
              JOIN scope s ON s.id=m.org_unit_id
              WHERE m.tenant_id=%s AND m.user_id=%s AND m.status='active'
                AND p.permission_key=%s
            ) AS allowed
        """, (self.config.org_unit_id,self.config.tenant_id,self.config.tenant_id,
              self.config.tenant_id,self.config.actor_user_id,permission)).fetchone()
        if not row or not row["allowed"]:
            raise PermissionError(f"Fehlende Berechtigung: {permission}")
    def _audit(self, conn, event, entity_type, entity_id, metadata):
        conn.execute("""INSERT INTO parish_audit_events
          (tenant_id,actor_user_id,org_unit_id,event_type,entity_type,entity_id,outcome,metadata)
          VALUES (%s,%s,%s,%s,%s,%s,'success',%s::jsonb)""",
          (self.config.tenant_id,self.config.actor_user_id,self.config.org_unit_id,
           event,entity_type,str(entity_id),json.dumps(metadata)))
    def list_org_units(self):
        with self._connect() as conn:
            self._set_context(conn); self._require(conn,"org.read")
            rows=conn.execute("""WITH RECURSIVE scope AS (
              SELECT id,parent_id,unit_type,unit_key,display_name,status,0 AS depth
              FROM parish_org_units WHERE id=%s AND tenant_id=%s
              UNION ALL SELECT c.id,c.parent_id,c.unit_type,c.unit_key,c.display_name,c.status,p.depth+1
              FROM parish_org_units c JOIN scope p ON c.parent_id=p.id WHERE c.tenant_id=%s)
              SELECT id,parent_id,unit_type,unit_key,display_name,status,depth FROM scope
              ORDER BY depth,display_name""",
              (self.config.org_unit_id,self.config.tenant_id,self.config.tenant_id)).fetchall()
            return [dict(x) for x in rows]
    def create_org_unit(self, unit_type, unit_key, display_name, parent_id):
        parents={"diocese":{None},"pastoral_region":{"diocese"},"parish":{"pastoral_region"},"parish_office":{"parish"}}
        if unit_type not in parents: raise ValueError("Ungültiger Organisationstyp.")
        if not unit_key.strip() or not display_name.strip(): raise ValueError("Schlüssel und Bezeichnung sind Pflichtfelder.")
        if unit_type=="diocese" and parent_id is not None: raise ValueError("Ein Bistum darf keinen Elternknoten besitzen.")
        if unit_type!="diocese" and parent_id is None: raise ValueError("Übergeordnete Organisationseinheit erforderlich.")
        with self._connect() as conn:
            self._set_context(conn); self._require(conn,"org.admin")
            if parent_id:
                parent=conn.execute("SELECT unit_type FROM parish_org_units WHERE id=%s AND tenant_id=%s",
                                    (parent_id,self.config.tenant_id)).fetchone()
                if not parent or parent["unit_type"] not in parents[unit_type]:
                    raise ValueError("Übergeordnete Organisationseinheit ist nicht zulässig.")
                self._require_scope(conn,parent_id)
            row=conn.execute("""INSERT INTO parish_org_units
              (id,tenant_id,parent_id,unit_type,unit_key,display_name)
              VALUES (%s,%s,%s,%s,%s,%s)
              RETURNING id,parent_id,unit_type,unit_key,display_name,status""",
              (str(uuid4()),self.config.tenant_id,parent_id,unit_type,unit_key.strip(),display_name.strip())).fetchone()
            self._audit(conn,"org_unit.created","parish_org_unit",row["id"],
                        {"unit_type":unit_type,"unit_key":unit_key.strip()})
            return dict(row)
    def list_users(self):
        with self._connect() as conn:
            self._set_context(conn); self._require(conn,"user.admin")
            rows=conn.execute("""SELECT u.id,u.email,u.display_name,u.status,
              count(m.id) FILTER (WHERE m.status='active') AS active_memberships
              FROM parish_users u LEFT JOIN parish_memberships m
              ON m.tenant_id=u.tenant_id AND m.user_id=u.id
              WHERE u.tenant_id=%s GROUP BY u.id ORDER BY u.display_name""",
              (self.config.tenant_id,)).fetchall()
            return [dict(x) for x in rows]
    def create_user(self,email,display_name):
        email=email.strip().lower(); display_name=display_name.strip()
        if "@" not in email or len(email)>320 or not display_name:
            raise ValueError("Gültige E-Mail-Adresse und Anzeigename erforderlich.")
        with self._connect() as conn:
            self._set_context(conn); self._require(conn,"user.admin")
            row=conn.execute("""INSERT INTO parish_users(tenant_id,email,display_name,status)
              VALUES (%s,%s,%s,'invited') RETURNING id,email,display_name,status""",
              (self.config.tenant_id,email,display_name)).fetchone()
            self._audit(conn,"user.invited","parish_user",row["id"],{"email":email})
            return dict(row)
    def list_roles(self):
        with self._connect() as conn:
            self._set_context(conn); self._require(conn,"user.admin")
            rows=conn.execute("""SELECT r.role_key,r.display_name,r.description,
              coalesce(array_agg(p.permission_key ORDER BY p.permission_key)
              FILTER (WHERE p.permission_key IS NOT NULL),ARRAY[]::text[]) AS permissions
              FROM parish_roles r LEFT JOIN parish_role_permissions rp ON rp.role_id=r.id
              LEFT JOIN parish_permissions p ON p.id=rp.permission_id
              GROUP BY r.id ORDER BY r.display_name""").fetchall()
            return [dict(x) for x in rows]
    def create_membership(self,user_id,org_unit_id,role_key):
        try: UUID(user_id); UUID(org_unit_id)
        except ValueError as exc: raise ValueError("Benutzer- und Organisationseinheits-ID müssen UUIDs sein.") from exc
        with self._connect() as conn:
            self._set_context(conn); self._require(conn,"user.admin")
            if role_key=="bistum_admin": self._require(conn,"tenant.admin")
            user=conn.execute("SELECT id FROM parish_users WHERE id=%s AND tenant_id=%s AND status<>'disabled'",
                              (user_id,self.config.tenant_id)).fetchone()
            org=conn.execute("SELECT id FROM parish_org_units WHERE id=%s AND tenant_id=%s",
                             (org_unit_id,self.config.tenant_id)).fetchone()
            role=conn.execute("SELECT id FROM parish_roles WHERE role_key=%s",(role_key,)).fetchone()
            if not user or not org or not role: raise ValueError("Benutzer, Organisationseinheit oder Rolle nicht gefunden.")
            self._require_scope(conn,org_unit_id)
            row=conn.execute("""INSERT INTO parish_memberships(tenant_id,user_id,org_unit_id,role_id,status)
              VALUES (%s,%s,%s,%s,'active')
              ON CONFLICT (tenant_id,user_id,org_unit_id,role_id) DO UPDATE SET status='active'
              RETURNING id,status""",
              (self.config.tenant_id,user_id,org_unit_id,role["id"])).fetchone()
            self._audit(conn,"membership.granted","parish_membership",row["id"],
                        {"user_id":user_id,"org_unit_id":org_unit_id,"role_key":role_key})
            return dict(row)
    def _require_scope(self,conn,target_org_id):
        row=conn.execute("""WITH RECURSIVE scope(id,parent_id) AS (
          SELECT id,parent_id FROM parish_org_units WHERE id=%s AND tenant_id=%s
          UNION ALL SELECT p.id,p.parent_id FROM parish_org_units p
          JOIN scope c ON c.parent_id=p.id WHERE p.tenant_id=%s)
          SELECT EXISTS(SELECT 1 FROM scope WHERE id=%s) AS allowed""",
          (target_org_id,self.config.tenant_id,self.config.tenant_id,self.config.org_unit_id)).fetchone()
        if not row or not row["allowed"]:
            raise PermissionError("Zielorganisation liegt außerhalb des eigenen Verwaltungsbereichs.")
