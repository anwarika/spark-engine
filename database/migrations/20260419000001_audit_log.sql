-- Audit Log: structured security/access log persisted to Postgres.
-- Written async (fire-and-forget) so it never blocks the hot path.

CREATE TABLE IF NOT EXISTS audit_log (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   text        NOT NULL,
  user_id     text        NOT NULL,
  key_id      uuid,                        -- NULL for header-auth requests
  action      text        NOT NULL,        -- e.g. 'generate', 'pin', 'key.create', 'key.revoke'
  resource_id text,                        -- component_id, pin_id, etc.
  ip          text,
  status_code integer,
  meta        jsonb       DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_tenant     ON audit_log(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_key        ON audit_log(key_id) WHERE key_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_action     ON audit_log(action);
