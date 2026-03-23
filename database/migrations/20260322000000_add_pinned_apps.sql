-- Pinned Apps: user-owned stable app slots that survive component regeneration.
-- A "pin" is the bookmark. The component underneath can be swapped via re-generation
-- but the pin's identity (id, slot_name, iframe URL) remains stable.

CREATE TABLE IF NOT EXISTS pinned_apps (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id    text        NOT NULL,
  user_id      text        NOT NULL,
  component_id uuid        NOT NULL REFERENCES components(id) ON DELETE RESTRICT,
  slot_name    text        NOT NULL,          -- user-visible label: "Pipeline Dashboard"
  description  text        DEFAULT '',
  icon         text        DEFAULT '',        -- emoji or icon name for nav rendering
  sort_order   integer     DEFAULT 0,         -- ordering in nav bar
  metadata     jsonb       DEFAULT '{}'::jsonb,
  pinned_at    timestamptz DEFAULT now(),
  updated_at   timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pinned_apps_tenant_user ON pinned_apps(tenant_id, user_id);
CREATE INDEX IF NOT EXISTS idx_pinned_apps_component   ON pinned_apps(component_id);

-- Each user gets one pin per slot name within a tenant (prevent duplicate bookmarks)
CREATE UNIQUE INDEX IF NOT EXISTS idx_pinned_apps_unique_slot
  ON pinned_apps(tenant_id, user_id, slot_name);

ALTER TABLE pinned_apps ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own pinned apps"
  ON pinned_apps FOR SELECT
  USING (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY "Users can insert own pinned apps"
  ON pinned_apps FOR INSERT
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY "Users can update own pinned apps"
  ON pinned_apps FOR UPDATE
  USING (tenant_id = current_setting('app.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY "Users can delete own pinned apps"
  ON pinned_apps FOR DELETE
  USING (tenant_id = current_setting('app.tenant_id', true));
