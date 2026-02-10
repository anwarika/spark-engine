-- Add content_hash for Content-Addressable Generation (CAG)
-- This hash represents the user's intent (normalized prompt + template + data profile)
-- Different from code_hash which represents the actual generated code

ALTER TABLE components
  ADD COLUMN IF NOT EXISTS content_hash text,
  ADD COLUMN IF NOT EXISTS prompt_normalized text,
  ADD COLUMN IF NOT EXISTS generation_metadata jsonb DEFAULT '{}'::jsonb;

-- Index for fast lookup by content hash
CREATE INDEX IF NOT EXISTS idx_components_content_hash ON components(content_hash);

-- Index for CAG queries (tenant + content_hash + status)
CREATE INDEX IF NOT EXISTS idx_components_cag_lookup ON components(tenant_id, content_hash, status) WHERE content_hash IS NOT NULL;

COMMENT ON COLUMN components.content_hash IS 'SHA256 hash of normalized prompt + template + data profile for CAG deduplication';
COMMENT ON COLUMN components.prompt_normalized IS 'Normalized version of the original user prompt for debugging';
COMMENT ON COLUMN components.generation_metadata IS 'Stores template_name, data_profile, reuse_count, original_component_id for CAG tracking';
