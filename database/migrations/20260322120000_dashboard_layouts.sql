-- Per-user dashboard canvas layout: grid items keyed by pin_id (react-grid-layout `i`).

CREATE TABLE IF NOT EXISTS dashboard_layouts (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   text        NOT NULL,
  user_id     text        NOT NULL,
  name        text        NOT NULL DEFAULT 'default',
  layout      jsonb       NOT NULL DEFAULT '[]'::jsonb,
  created_at  timestamptz DEFAULT now(),
  updated_at  timestamptz DEFAULT now(),
  UNIQUE (tenant_id, user_id, name)
);

CREATE INDEX IF NOT EXISTS idx_dashboard_layouts_tenant_user
  ON dashboard_layouts (tenant_id, user_id);

ALTER TABLE dashboard_layouts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own dashboard layouts"
  ON dashboard_layouts FOR SELECT
  USING (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY "Users can insert own dashboard layouts"
  ON dashboard_layouts FOR INSERT
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY "Users can update own dashboard layouts"
  ON dashboard_layouts FOR UPDATE
  USING (tenant_id = current_setting('app.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY "Users can delete own dashboard layouts"
  ON dashboard_layouts FOR DELETE
  USING (tenant_id = current_setting('app.tenant_id', true));
