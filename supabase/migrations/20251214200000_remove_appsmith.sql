-- Remove Appsmith-related columns from chat_messages table
ALTER TABLE chat_messages DROP COLUMN IF EXISTS appsmith_path;
ALTER TABLE chat_messages DROP COLUMN IF EXISTS microapp_kind;

