-- Component catalog/templates system
-- Allows saving and reusing generated components

CREATE TABLE IF NOT EXISTS component_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL,
  user_id UUID,
  name TEXT NOT NULL,
  description TEXT,
  category TEXT, -- 'chart', 'table', 'card', 'dashboard', 'list', 'custom'
  tags TEXT[], -- searchable tags
  solidjs_code TEXT NOT NULL,
  code_hash TEXT NOT NULL,
  compiled_bundle TEXT,
  bundle_size_bytes INTEGER,
  is_public BOOLEAN DEFAULT false, -- share across tenants
  usage_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_templates_tenant_category ON component_templates(tenant_id, category);
CREATE INDEX idx_templates_tags ON component_templates USING GIN(tags);
CREATE INDEX idx_templates_public ON component_templates(is_public) WHERE is_public = true;
CREATE INDEX idx_templates_usage ON component_templates(usage_count DESC);

-- RLS policies
ALTER TABLE component_templates ENABLE ROW LEVEL SECURITY;

-- Users can see their own templates and public templates
CREATE POLICY "Users can view own and public templates"
ON component_templates FOR SELECT
USING (
  tenant_id = current_setting('app.tenant_id', true)::UUID
  OR is_public = true
);

-- Users can insert their own templates
CREATE POLICY "Users can insert own templates"
ON component_templates FOR INSERT
WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::UUID);

-- Users can update their own templates
CREATE POLICY "Users can update own templates"
ON component_templates FOR UPDATE
USING (tenant_id = current_setting('app.tenant_id', true)::UUID);

-- Users can delete their own templates
CREATE POLICY "Users can delete own templates"
ON component_templates FOR DELETE
USING (tenant_id = current_setting('app.tenant_id', true)::UUID);

