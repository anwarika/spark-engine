-- Add microapp reference fields to chat_messages to support Appsmith and other microapp types.

ALTER TABLE IF EXISTS chat_messages
  ADD COLUMN IF NOT EXISTS microapp_kind text,
  ADD COLUMN IF NOT EXISTS appsmith_path text;

-- Optional: constrain known kinds (keep loose to avoid migration pain during early iteration)
-- ALTER TABLE chat_messages
--   ADD CONSTRAINT chat_messages_microapp_kind_check
--   CHECK (microapp_kind IN ('spark_component', 'appsmith_app'));

CREATE INDEX IF NOT EXISTS idx_chat_messages_microapp_kind ON chat_messages(microapp_kind);


