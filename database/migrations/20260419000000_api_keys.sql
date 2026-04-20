-- API Keys: first-class credentials for Spark integrators.
-- Keys replace raw base64(tenant:user) Bearer tokens with hashed, revocable,
-- scoped keys prefixed sk_live_... (similar to Stripe/OpenAI key patterns).

CREATE TABLE IF NOT EXISTS api_keys (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       text        NOT NULL,
  user_id         text        NOT NULL,
  key_hash        text        NOT NULL UNIQUE,   -- SHA-256 of the raw key
  key_prefix      text        NOT NULL,          -- first 8 chars of raw key for display (e.g. sk_live_ab)
  label           text        NOT NULL DEFAULT 'Default Key',
  scopes          text[]      NOT NULL DEFAULT ARRAY['generate','read'],
  rate_limit_rpm  integer     NOT NULL DEFAULT 60,
  created_at      timestamptz NOT NULL DEFAULT now(),
  last_used_at    timestamptz,
  revoked_at      timestamptz
);

CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash   ON api_keys(key_hash);

ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Tenants can view own api keys"
  ON api_keys FOR SELECT
  USING (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY "Tenants can insert own api keys"
  ON api_keys FOR INSERT
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY "Tenants can update own api keys"
  ON api_keys FOR UPDATE
  USING (tenant_id = current_setting('app.tenant_id', true));
