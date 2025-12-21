/*
  # Spark Service Database Schema
  
  Creates the complete database schema for the Spark AI-powered micro app generation service.
  
  1. New Tables
    - `components`
      - Stores generated Solid.js micro-app components with metadata
      - `id` (uuid, primary key)
      - `tenant_id` (text) - Organization identifier for multi-tenant isolation
      - `user_id` (text) - User who created the component
      - `name` (text) - Human-readable component name
      - `description` (text) - Component description
      - `solidjs_code` (text) - Original Solid.js source code
      - `code_hash` (text) - SHA256 hash for caching and deduplication
      - `version` (text) - Semantic version
      - `validated` (boolean) - Passed security validation
      - `compiled` (boolean) - Successfully compiled
      - `compiled_bundle` (text) - Compiled JavaScript artifact
      - `bundle_size_bytes` (integer) - Size of compiled bundle
      - `status` (text) - active, archived
      - `created_at` (timestamptz)
      - `updated_at` (timestamptz)
      
    - `chat_sessions`
      - Tracks user chat sessions
      - `id` (uuid, primary key)
      - `tenant_id` (text)
      - `user_id` (text)
      - `session_id` (text) - Unique session identifier
      - `started_at` (timestamptz)
      - `last_activity_at` (timestamptz)
      - `metadata` (jsonb) - Flexible metadata storage
      
    - `chat_messages`
      - Stores conversation history
      - `id` (uuid, primary key)
      - `session_id` (uuid, foreign key)
      - `role` (text) - user, assistant, system
      - `content` (text) - Message content
      - `component_id` (uuid, nullable foreign key) - Links to generated component
      - `llm_model` (text) - Model used for generation
      - `reasoning` (text) - LLM reasoning for component generation
      - `created_at` (timestamptz)
      
    - `component_executions`
      - Tracks component runtime performance
      - `id` (uuid, primary key)
      - `component_id` (uuid, foreign key)
      - `execution_time_ms` (integer)
      - `success` (boolean)
      - `error_message` (text)
      - `executed_at` (timestamptz)
      
    - `component_feedback`
      - User ratings and feedback
      - `id` (uuid, primary key)
      - `component_id` (uuid, foreign key)
      - `user_id` (text)
      - `rating` (integer) - 1 (thumbs down) or 5 (thumbs up)
      - `feedback_text` (text)
      - `created_at` (timestamptz)
      
    - `audit_logs`
      - Comprehensive audit trail
      - `id` (uuid, primary key)
      - `tenant_id` (text)
      - `user_id` (text)
      - `action` (text) - Action type
      - `resource_type` (text) - Table/entity name
      - `resource_id` (uuid) - Resource identifier
      - `details` (jsonb) - Additional context
      - `timestamp` (timestamptz)
      
  2. Security
    - Enable RLS on all tables
    - Add policies for tenant isolation
    - Authenticated users can only access their tenant's data
*/

-- Components table
CREATE TABLE IF NOT EXISTS components (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  user_id text NOT NULL,
  name text NOT NULL,
  description text DEFAULT '',
  solidjs_code text NOT NULL,
  code_hash text NOT NULL,
  version text DEFAULT '1.0.0',
  validated boolean DEFAULT false,
  compiled boolean DEFAULT false,
  compiled_bundle text,
  bundle_size_bytes integer DEFAULT 0,
  status text DEFAULT 'active',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_components_tenant ON components(tenant_id);
CREATE INDEX IF NOT EXISTS idx_components_user ON components(user_id);
CREATE INDEX IF NOT EXISTS idx_components_hash ON components(code_hash);
CREATE INDEX IF NOT EXISTS idx_components_status ON components(status);

ALTER TABLE components ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own tenant components"
  ON components FOR SELECT
  USING (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY "Users can insert own tenant components"
  ON components FOR INSERT
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY "Users can update own tenant components"
  ON components FOR UPDATE
  USING (tenant_id = current_setting('app.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY "Users can delete own tenant components"
  ON components FOR DELETE
  USING (tenant_id = current_setting('app.tenant_id', true));

-- Chat sessions table
CREATE TABLE IF NOT EXISTS chat_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  user_id text NOT NULL,
  session_id text UNIQUE NOT NULL,
  started_at timestamptz DEFAULT now(),
  last_activity_at timestamptz DEFAULT now(),
  metadata jsonb DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_tenant ON chat_sessions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_session_id ON chat_sessions(session_id);

ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own tenant sessions"
  ON chat_sessions FOR SELECT
  USING (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY "Users can insert own tenant sessions"
  ON chat_sessions FOR INSERT
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY "Users can update own tenant sessions"
  ON chat_sessions FOR UPDATE
  USING (tenant_id = current_setting('app.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- Chat messages table
CREATE TABLE IF NOT EXISTS chat_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role text NOT NULL,
  content text NOT NULL,
  component_id uuid REFERENCES components(id) ON DELETE SET NULL,
  llm_model text DEFAULT '',
  reasoning text DEFAULT '',
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_component ON chat_messages(component_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created ON chat_messages(created_at);

ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view messages in own tenant sessions"
  ON chat_messages FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM chat_sessions
      WHERE chat_sessions.id = chat_messages.session_id
      AND chat_sessions.tenant_id = current_setting('app.tenant_id', true)
    )
  );

CREATE POLICY "Users can insert messages in own tenant sessions"
  ON chat_messages FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM chat_sessions
      WHERE chat_sessions.id = chat_messages.session_id
      AND chat_sessions.tenant_id = current_setting('app.tenant_id', true)
    )
  );

-- Component executions table
CREATE TABLE IF NOT EXISTS component_executions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  component_id uuid NOT NULL REFERENCES components(id) ON DELETE CASCADE,
  execution_time_ms integer DEFAULT 0,
  success boolean DEFAULT true,
  error_message text DEFAULT '',
  executed_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_component_executions_component ON component_executions(component_id);
CREATE INDEX IF NOT EXISTS idx_component_executions_executed ON component_executions(executed_at);

ALTER TABLE component_executions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view executions for own tenant components"
  ON component_executions FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM components
      WHERE components.id = component_executions.component_id
      AND components.tenant_id = current_setting('app.tenant_id', true)
    )
  );

CREATE POLICY "Users can insert executions for own tenant components"
  ON component_executions FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM components
      WHERE components.id = component_executions.component_id
      AND components.tenant_id = current_setting('app.tenant_id', true)
    )
  );

-- Component feedback table
CREATE TABLE IF NOT EXISTS component_feedback (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  component_id uuid NOT NULL REFERENCES components(id) ON DELETE CASCADE,
  user_id text NOT NULL,
  rating integer NOT NULL CHECK (rating IN (1, 5)),
  feedback_text text DEFAULT '',
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_component_feedback_component ON component_feedback(component_id);
CREATE INDEX IF NOT EXISTS idx_component_feedback_user ON component_feedback(user_id);

ALTER TABLE component_feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view feedback for own tenant components"
  ON component_feedback FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM components
      WHERE components.id = component_feedback.component_id
      AND components.tenant_id = current_setting('app.tenant_id', true)
    )
  );

CREATE POLICY "Users can insert feedback for own tenant components"
  ON component_feedback FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM components
      WHERE components.id = component_feedback.component_id
      AND components.tenant_id = current_setting('app.tenant_id', true)
    )
  );

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  user_id text NOT NULL,
  action text NOT NULL,
  resource_type text NOT NULL,
  resource_id uuid,
  details jsonb DEFAULT '{}'::jsonb,
  timestamp timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant ON audit_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own tenant audit logs"
  ON audit_logs FOR SELECT
  USING (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY "Users can insert own tenant audit logs"
  ON audit_logs FOR INSERT
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
