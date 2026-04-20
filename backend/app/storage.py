from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import logging
import json
from datetime import datetime
import asyncio
from app.config import settings
from supabase import create_client, Client
import asyncpg

logger = logging.getLogger(__name__)

class Storage(ABC):
    """Abstract base class for database storage operations."""

    @abstractmethod
    async def get_or_create_session(self, tenant_id: str, user_id: str, session_id: str) -> str:
        """Get existing session ID (DB UUID) or create a new one."""
        pass

    @abstractmethod
    async def update_session_activity(self, db_id: str):
        pass

    @abstractmethod
    async def get_chat_history(self, session_db_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def save_chat_message(self, session_db_id: str, role: str, content: str, 
                              component_id: Optional[str] = None, 
                              llm_model: Optional[str] = None, 
                              reasoning: Optional[str] = None):
        pass

    @abstractmethod
    async def create_component(self, component_data: Dict[str, Any]) -> str:
        """Returns the ID of the created component."""
        pass

    @abstractmethod
    async def get_component(self, component_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def list_components(self, tenant_id: str, limit: int = 20, offset: int = 0, status: Optional[str] = "active") -> Dict[str, Any]:
        """Returns dict with 'components' (list) and 'total' (int)."""
        pass

    @abstractmethod
    async def update_component_status(self, component_id: str, tenant_id: str, status: str) -> bool:
        pass

    @abstractmethod
    async def add_component_feedback(self, component_id: str, user_id: str, rating: int, feedback_text: str):
        pass

    @abstractmethod
    async def get_component_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def list_component_templates(self, tenant_id: str, category: Optional[str] = None, is_public: Optional[bool] = None, tag: Optional[str] = None, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Returns {'templates': [], 'total': int}"""
        pass
    
    @abstractmethod
    async def create_or_update_template(self, tenant_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Returns the created/updated template."""
        pass
    
    @abstractmethod
    async def increment_template_usage(self, template_id: str):
        pass
    
    @abstractmethod
    async def delete_template(self, template_id: str, tenant_id: str) -> bool:
        pass
    
    @abstractmethod
    async def find_component_by_content_hash(self, tenant_id: str, content_hash: str) -> Optional[Dict[str, Any]]:
        """
        Find an existing component by content hash (CAG lookup).
        Returns the most recently created active component matching the hash.
        """
        pass

    # ------------------------------------------------------------------
    # Pinned Apps
    # ------------------------------------------------------------------

    @abstractmethod
    async def create_pinned_app(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Pin a component. Returns the created pinned_app row."""
        pass

    @abstractmethod
    async def get_pinned_app(self, pin_id: str, tenant_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def list_pinned_apps(self, tenant_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Returns all pinned apps for a user, joined with component metadata."""
        pass

    @abstractmethod
    async def update_pinned_app_component(self, pin_id: str, tenant_id: str, user_id: str,
                                          component_id: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Atomically swap the component_id under a pin (used after re-generation)."""
        pass

    @abstractmethod
    async def update_pinned_app_meta(self, pin_id: str, tenant_id: str, user_id: str,
                                     updates: Dict[str, Any]) -> bool:
        """Update mutable fields: slot_name, description, icon, sort_order, metadata."""
        pass

    @abstractmethod
    async def delete_pinned_app(self, pin_id: str, tenant_id: str, user_id: str) -> bool:
        pass

    # ------------------------------------------------------------------
    # API Keys
    # ------------------------------------------------------------------

    @abstractmethod
    async def create_api_key(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new API key row. Returns the created row."""
        pass

    @abstractmethod
    async def get_api_key_by_hash(self, key_hash: str) -> Optional[Dict[str, Any]]:
        """Look up a key by its SHA-256 hash. Returns row or None."""
        pass

    @abstractmethod
    async def list_api_keys(self, tenant_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Return all non-revoked keys for a user."""
        pass

    @abstractmethod
    async def revoke_api_key(self, key_id: str, tenant_id: str, user_id: str) -> bool:
        """Set revoked_at = now(). Returns True if a row was updated."""
        pass

    @abstractmethod
    async def touch_api_key(self, key_id: str):
        """Update last_used_at = now() (fire-and-forget)."""
        pass

    # ------------------------------------------------------------------
    # Audit Log
    # ------------------------------------------------------------------

    @abstractmethod
    async def write_audit_log(self, entry: Dict[str, Any]):
        """Append one entry to the audit_log table (best-effort)."""
        pass

    # ------------------------------------------------------------------
    # Dashboard layouts
    # ------------------------------------------------------------------

    @abstractmethod
    async def get_dashboard_layout(
        self, tenant_id: str, user_id: str, name: str = "default"
    ) -> Optional[Dict[str, Any]]:
        """Return row dict with keys name, layout (list), updated_at or None."""
        pass

    @abstractmethod
    async def upsert_dashboard_layout(
        self, tenant_id: str, user_id: str, name: str, layout: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Insert or update layout JSON; returns { name, layout, updated_at }."""
        pass


class SupabaseStorage(Storage):
    def __init__(self, url: str, key: str):
        self.client: Client = create_client(url, key)

    def _set_tenant(self, tenant_id: str):
        try:
            self.client.rpc('set_config', {'setting': 'app.tenant_id', 'value': tenant_id}).execute()
        except Exception:
            pass

    async def get_or_create_session(self, tenant_id: str, user_id: str, session_id: str) -> str:
        self._set_tenant(tenant_id)
        result = self.client.table("chat_sessions").select("id").eq("session_id", session_id).execute()
        
        if result.data:
            return result.data[0]["id"]
        
        new_session = self.client.table("chat_sessions").insert({
            "session_id": session_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "started_at": datetime.utcnow().isoformat(),
            "last_activity_at": datetime.utcnow().isoformat()
        }).execute()
        return new_session.data[0]["id"]

    async def update_session_activity(self, db_id: str):
        try:
            self.client.table("chat_sessions").update({
                "last_activity_at": datetime.utcnow().isoformat()
            }).eq("id", db_id).execute()
        except Exception as e:
            logger.warning(f"Failed to update session activity: {e}")

    async def get_chat_history(self, session_db_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        result = self.client.table("chat_messages").select("role, content").eq(
            "session_id", session_db_id
        ).order("created_at").limit(limit).execute()
        return result.data if result.data else []

    async def save_chat_message(self, session_db_id: str, role: str, content: str, 
                              component_id: Optional[str] = None, 
                              llm_model: Optional[str] = None, 
                              reasoning: Optional[str] = None):
        data = {
            "session_id": session_db_id,
            "role": role,
            "content": content
        }
        if component_id: data["component_id"] = component_id
        if llm_model: data["llm_model"] = llm_model
        if reasoning: data["reasoning"] = reasoning
        
        self.client.table("chat_messages").insert(data).execute()

    async def create_component(self, component_data: Dict[str, Any]) -> str:
        self._set_tenant(component_data.get("tenant_id", ""))
        result = self.client.table("components").insert(component_data).execute()
        return result.data[0]["id"]

    async def get_component(self, component_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        self._set_tenant(tenant_id)
        result = self.client.table("components").select("*").eq("id", component_id).eq("tenant_id", tenant_id).execute()
        return result.data[0] if result.data else None

    async def list_components(self, tenant_id: str, limit: int = 20, offset: int = 0, status: Optional[str] = "active") -> Dict[str, Any]:
        self._set_tenant(tenant_id)
        query = self.client.table("components").select(
            "id, name, description, version, bundle_size_bytes, status, created_at, updated_at", count="exact"
        ).eq("tenant_id", tenant_id)
        
        if status:
            query = query.eq("status", status)
            
        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return {
            "components": result.data,
            "total": result.count or len(result.data)
        }

    async def update_component_status(self, component_id: str, tenant_id: str, status: str) -> bool:
        self._set_tenant(tenant_id)
        result = self.client.table("components").update({"status": status}).eq("id", component_id).eq("tenant_id", tenant_id).execute()
        return bool(result.data)

    async def add_component_feedback(self, component_id: str, user_id: str, rating: int, feedback_text: str):
        self.client.table("component_feedback").insert({
            "component_id": component_id,
            "user_id": user_id,
            "rating": rating,
            "feedback_text": feedback_text
        }).execute()

    async def get_component_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        result = self.client.table("component_templates").select("*").eq("id", template_id).execute()
        return result.data[0] if result.data else None

    async def list_component_templates(self, tenant_id: str, category: Optional[str] = None, is_public: Optional[bool] = None, tag: Optional[str] = None, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        self._set_tenant(tenant_id)
        query = self.client.table("component_templates").select(
            "id, name, description, category, tags, code_hash, bundle_size_bytes, is_public, usage_count, created_at, updated_at",
            count="exact"
        )
        
        # In Supabase RLS policies usually handle filtering by tenant OR public. 
        # But if we rely on RLS, we just select.
        # If we need manual filter:
        if category:
            query = query.eq("category", category)
        if is_public is not None:
            query = query.eq("is_public", is_public)
        if tag:
            query = query.contains("tags", [tag])
            
        result = query.order("usage_count", desc=True).range(offset, offset + limit - 1).execute()
        return {
            "templates": result.data,
            "total": result.count or len(result.data)
        }

    async def create_or_update_template(self, tenant_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        self._set_tenant(tenant_id)
        existing = self.client.table("component_templates").select("id").eq("name", data["name"]).eq("tenant_id", tenant_id).execute()
        
        if existing.data:
            result = self.client.table("component_templates").update(data).eq("id", existing.data[0]["id"]).execute()
        else:
            result = self.client.table("component_templates").insert(data).execute()
        return result.data[0] if result.data else {}

    async def increment_template_usage(self, template_id: str):
        # This is a bit racy without RPC but simple update is okay for now
        # Ideally: rpc('increment_usage', {template_id})
        try:
            current = await self.get_component_template(template_id)
            if current:
                self.client.table("component_templates").update({
                    "usage_count": (current.get("usage_count") or 0) + 1
                }).eq("id", template_id).execute()
        except Exception:
            pass

    async def delete_template(self, template_id: str, tenant_id: str) -> bool:
        self._set_tenant(tenant_id)
        self.client.table("component_templates").delete().eq("id", template_id).execute()
        return True

    async def find_component_by_content_hash(self, tenant_id: str, content_hash: str) -> Optional[Dict[str, Any]]:
        self._set_tenant(tenant_id)
        result = (
            self.client.table("components")
            .select("*")
            .eq("tenant_id", tenant_id)
            .eq("content_hash", content_hash)
            .eq("status", "active")
            .eq("compiled", True)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    # ------------------------------------------------------------------
    # Pinned Apps — Supabase
    # ------------------------------------------------------------------

    async def create_pinned_app(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self._set_tenant(data.get("tenant_id", ""))
        result = self.client.table("pinned_apps").insert(data).execute()
        return result.data[0] if result.data else {}

    async def get_pinned_app(self, pin_id: str, tenant_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        self._set_tenant(tenant_id)
        result = (
            self.client.table("pinned_apps")
            .select("*")
            .eq("id", pin_id)
            .eq("tenant_id", tenant_id)
            .eq("user_id", user_id)
            .execute()
        )
        return result.data[0] if result.data else None

    async def list_pinned_apps(self, tenant_id: str, user_id: str) -> List[Dict[str, Any]]:
        self._set_tenant(tenant_id)
        result = (
            self.client.table("pinned_apps")
            .select("*, components(id, name, description, version, bundle_size_bytes, status, created_at, updated_at)")
            .eq("tenant_id", tenant_id)
            .eq("user_id", user_id)
            .order("sort_order")
            .execute()
        )
        return result.data if result.data else []

    async def update_pinned_app_component(self, pin_id: str, tenant_id: str, user_id: str,
                                          component_id: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        self._set_tenant(tenant_id)
        update_data: Dict[str, Any] = {
            "component_id": component_id,
            "updated_at": datetime.utcnow().isoformat(),
        }
        if metadata is not None:
            update_data["metadata"] = metadata
        result = (
            self.client.table("pinned_apps")
            .update(update_data)
            .eq("id", pin_id)
            .eq("tenant_id", tenant_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(result.data)

    async def update_pinned_app_meta(self, pin_id: str, tenant_id: str, user_id: str,
                                     updates: Dict[str, Any]) -> bool:
        self._set_tenant(tenant_id)
        updates["updated_at"] = datetime.utcnow().isoformat()
        result = (
            self.client.table("pinned_apps")
            .update(updates)
            .eq("id", pin_id)
            .eq("tenant_id", tenant_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(result.data)

    async def delete_pinned_app(self, pin_id: str, tenant_id: str, user_id: str) -> bool:
        self._set_tenant(tenant_id)
        self.client.table("pinned_apps").delete().eq("id", pin_id).eq("tenant_id", tenant_id).eq("user_id", user_id).execute()
        return True

    # ------------------------------------------------------------------
    # API Keys — Supabase
    # ------------------------------------------------------------------

    async def create_api_key(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self._set_tenant(data.get("tenant_id", ""))
        result = self.client.table("api_keys").insert(data).execute()
        return result.data[0] if result.data else {}

    async def get_api_key_by_hash(self, key_hash: str) -> Optional[Dict[str, Any]]:
        result = self.client.table("api_keys").select("*").eq("key_hash", key_hash).limit(1).execute()
        return result.data[0] if result.data else None

    async def list_api_keys(self, tenant_id: str, user_id: str) -> List[Dict[str, Any]]:
        self._set_tenant(tenant_id)
        result = (
            self.client.table("api_keys")
            .select("id, label, key_prefix, scopes, rate_limit_rpm, created_at, last_used_at, revoked_at")
            .eq("tenant_id", tenant_id)
            .eq("user_id", user_id)
            .is_("revoked_at", "null")
            .order("created_at", desc=True)
            .execute()
        )
        return result.data if result.data else []

    async def revoke_api_key(self, key_id: str, tenant_id: str, user_id: str) -> bool:
        self._set_tenant(tenant_id)
        result = (
            self.client.table("api_keys")
            .update({"revoked_at": datetime.utcnow().isoformat()})
            .eq("id", key_id)
            .eq("tenant_id", tenant_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(result.data)

    async def touch_api_key(self, key_id: str):
        try:
            self.client.table("api_keys").update({
                "last_used_at": datetime.utcnow().isoformat()
            }).eq("id", key_id).execute()
        except Exception:
            pass

    async def write_audit_log(self, entry: Dict[str, Any]):
        try:
            self.client.table("audit_log").insert(entry).execute()
        except Exception as e:
            logger.warning(f"Audit log write failed: {e}")

    # ------------------------------------------------------------------
    # Dashboard layouts — Supabase
    # ------------------------------------------------------------------

    async def get_dashboard_layout(
        self, tenant_id: str, user_id: str, name: str = "default"
    ) -> Optional[Dict[str, Any]]:
        self._set_tenant(tenant_id)
        result = (
            self.client.table("dashboard_layouts")
            .select("name, layout, updated_at")
            .eq("tenant_id", tenant_id)
            .eq("user_id", user_id)
            .eq("name", name)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        row = result.data[0]
        layout = row.get("layout")
        if layout is None:
            layout = []
        return {"name": row["name"], "layout": layout, "updated_at": row.get("updated_at")}

    async def upsert_dashboard_layout(
        self, tenant_id: str, user_id: str, name: str, layout: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        self._set_tenant(tenant_id)
        now = datetime.utcnow().isoformat()
        existing = (
            self.client.table("dashboard_layouts")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("user_id", user_id)
            .eq("name", name)
            .limit(1)
            .execute()
        )
        if existing.data:
            self.client.table("dashboard_layouts").update({
                "layout": layout,
                "updated_at": now,
            }).eq("id", existing.data[0]["id"]).execute()
        else:
            self.client.table("dashboard_layouts").insert({
                "tenant_id": tenant_id,
                "user_id": user_id,
                "name": name,
                "layout": layout,
                "updated_at": now,
            }).execute()
        return {"name": name, "layout": layout, "updated_at": now}


class PostgresStorage(Storage):
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._pool = None

    async def _get_pool(self):
        if not self._pool:
            self._pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=10)
        return self._pool

    async def get_or_create_session(self, tenant_id: str, user_id: str, session_id: str) -> str:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT id FROM chat_sessions WHERE session_id = $1", session_id)
            if row:
                return str(row['id'])
            
            val = await conn.fetchval("""
                INSERT INTO chat_sessions (session_id, tenant_id, user_id, started_at, last_activity_at)
                VALUES ($1, $2, $3, NOW(), NOW())
                RETURNING id
            """, session_id, tenant_id, user_id)
            return str(val)

    async def update_session_activity(self, db_id: str):
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE chat_sessions SET last_activity_at = NOW() WHERE id = $1::uuid", db_id)

    async def get_chat_history(self, session_db_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT role, content FROM chat_messages 
                WHERE session_id = $1::uuid 
                ORDER BY created_at ASC 
                LIMIT $2
            """, session_db_id, limit)
            return [dict(row) for row in rows]

    async def save_chat_message(self, session_db_id: str, role: str, content: str, 
                              component_id: Optional[str] = None, 
                              llm_model: Optional[str] = None, 
                              reasoning: Optional[str] = None):
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO chat_messages (session_id, role, content, component_id, llm_model, reasoning, created_at)
                VALUES ($1::uuid, $2, $3, $4::uuid, $5, $6, NOW())
            """, session_db_id, role, content, component_id, llm_model, reasoning)

    async def create_component(self, component_data: Dict[str, Any]) -> str:
        pool = await self._get_pool()
        fields = list(component_data.keys())
        values = list(component_data.values())
        placeholders = [f"${i+1}" for i in range(len(values))]
        
        stmt = f"INSERT INTO components ({', '.join(fields)}) VALUES ({', '.join(placeholders)}) RETURNING id"
        
        async with pool.acquire() as conn:
            val = await conn.fetchval(stmt, *values)
            return str(val)

    async def get_component(self, component_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM components WHERE id = $1::uuid AND tenant_id = $2
            """, component_id, tenant_id)
            if row:
                d = dict(row)
                d['id'] = str(d['id'])
                d['created_at'] = d['created_at'].isoformat() if d['created_at'] else None
                d['updated_at'] = d['updated_at'].isoformat() if d['updated_at'] else None
                return d
            return None

    async def list_components(self, tenant_id: str, limit: int = 20, offset: int = 0, status: Optional[str] = "active") -> Dict[str, Any]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            where_clause = "WHERE tenant_id = $1"
            params = [tenant_id]
            if status:
                where_clause += f" AND status = ${len(params)+1}"
                params.append(status)
            
            total = await conn.fetchval(f"SELECT COUNT(*) FROM components {where_clause}", *params)
            
            stmt = f"""
                SELECT id, name, description, version, bundle_size_bytes, status, created_at, updated_at
                FROM components {where_clause}
                ORDER BY created_at DESC
                LIMIT ${len(params)+1} OFFSET ${len(params)+2}
            """
            rows = await conn.fetch(stmt, *params, limit, offset)
            
            components = []
            for row in rows:
                d = dict(row)
                d['id'] = str(d['id'])
                d['created_at'] = d['created_at'].isoformat() if d['created_at'] else None
                d['updated_at'] = d['updated_at'].isoformat() if d['updated_at'] else None
                components.append(d)
                
            return {"components": components, "total": total}

    async def update_component_status(self, component_id: str, tenant_id: str, status: str) -> bool:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE components SET status = $1 WHERE id = $2::uuid AND tenant_id = $3
            """, status, component_id, tenant_id)
            return "UPDATE 0" not in result

    async def add_component_feedback(self, component_id: str, user_id: str, rating: int, feedback_text: str):
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO component_feedback (component_id, user_id, rating, feedback_text, created_at)
                VALUES ($1::uuid, $2, $3, $4, NOW())
            """, component_id, user_id, rating, feedback_text)

    async def get_component_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM component_templates WHERE id = $1::uuid", template_id)
            if row:
                d = dict(row)
                d['id'] = str(d['id'])
                d['tenant_id'] = str(d['tenant_id'])
                return d
            return None

    async def list_component_templates(self, tenant_id: str, category: Optional[str] = None, is_public: Optional[bool] = None, tag: Optional[str] = None, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            # Logic: (tenant_id = X OR is_public = true) AND filters
            where_parts = ["(tenant_id = $1::uuid OR is_public = true)"]
            params = [tenant_id]
            
            if category:
                where_parts.append(f"category = ${len(params)+1}")
                params.append(category)
            
            if is_public is not None:
                where_parts.append(f"is_public = ${len(params)+1}")
                params.append(is_public)
                
            if tag:
                # Postgres array containment
                where_parts.append(f"${len(params)+1} = ANY(tags)")
                params.append(tag)
                
            where_clause = " WHERE " + " AND ".join(where_parts)
            
            # Count
            total = await conn.fetchval(f"SELECT COUNT(*) FROM component_templates {where_clause}", *params)
            
            # Select
            stmt = f"""
                SELECT id, name, description, category, tags, code_hash, bundle_size_bytes, is_public, usage_count, created_at, updated_at
                FROM component_templates {where_clause}
                ORDER BY usage_count DESC
                LIMIT ${len(params)+1} OFFSET ${len(params)+2}
            """
            rows = await conn.fetch(stmt, *params, limit, offset)
            
            templates = []
            for row in rows:
                d = dict(row)
                d['id'] = str(d['id'])
                # d['tenant_id'] is not selected but if needed we should select it
                d['created_at'] = d['created_at'].isoformat() if d['created_at'] else None
                d['updated_at'] = d['updated_at'].isoformat() if d['updated_at'] else None
                templates.append(d)
                
            return {"templates": templates, "total": total}

    async def create_or_update_template(self, tenant_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            existing = await conn.fetchrow("""
                SELECT id FROM component_templates WHERE name = $1 AND tenant_id = $2::uuid
            """, data['name'], tenant_id)
            
            if existing:
                # Update
                # We update specific fields
                stmt = """
                    UPDATE component_templates 
                    SET description=$1, category=$2, tags=$3, solidjs_code=$4, compiled_bundle=$5, 
                        bundle_size_bytes=$6, is_public=$7, updated_at=NOW()
                    WHERE id=$8
                    RETURNING *
                """
                row = await conn.fetchrow(stmt, 
                    data.get('description'), data.get('category'), data.get('tags'),
                    data.get('solidjs_code'), data.get('compiled_bundle'), data.get('bundle_size_bytes'),
                    data.get('is_public'), existing['id']
                )
            else:
                # Insert
                stmt = """
                    INSERT INTO component_templates (tenant_id, user_id, name, description, category, tags, solidjs_code, code_hash, compiled_bundle, bundle_size_bytes, is_public, usage_count)
                    VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, 0)
                    RETURNING *
                """
                row = await conn.fetchrow(stmt,
                    tenant_id, data.get('user_id'), data['name'], data.get('description'), data.get('category'),
                    data.get('tags'), data.get('solidjs_code'), data.get('code_hash'), 
                    data.get('compiled_bundle'), data.get('bundle_size_bytes'), data.get('is_public', False)
                )
            
            if row:
                d = dict(row)
                d['id'] = str(d['id'])
                d['created_at'] = d['created_at'].isoformat() if d['created_at'] else None
                d['updated_at'] = d['updated_at'].isoformat() if d['updated_at'] else None
                return d
            return {}

    async def increment_template_usage(self, template_id: str):
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE component_templates SET usage_count = usage_count + 1 WHERE id = $1::uuid", template_id)

    async def delete_template(self, template_id: str, tenant_id: str) -> bool:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            # We must check tenant_id
            result = await conn.execute("DELETE FROM component_templates WHERE id = $1::uuid AND tenant_id = $2::uuid", template_id, tenant_id)
            return "DELETE 0" not in result
    
    async def find_component_by_content_hash(self, tenant_id: str, content_hash: str) -> Optional[Dict[str, Any]]:
        """Find existing component by content hash for CAG reuse"""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM components
                WHERE tenant_id = $1
                  AND content_hash = $2
                  AND status = 'active'
                  AND compiled = TRUE
                ORDER BY created_at DESC
                LIMIT 1
            """, tenant_id, content_hash)

            if row:
                d = dict(row)
                d['id'] = str(d['id'])
                d['created_at'] = d['created_at'].isoformat() if d['created_at'] else None
                d['updated_at'] = d['updated_at'].isoformat() if d['updated_at'] else None
                return d
            return None

    # ------------------------------------------------------------------
    # Pinned Apps — Postgres
    # ------------------------------------------------------------------

    async def create_pinned_app(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pool = await self._get_pool()
        fields = list(data.keys())
        values = list(data.values())
        placeholders = [f"${i+1}" for i in range(len(values))]
        stmt = f"""
            INSERT INTO pinned_apps ({', '.join(fields)})
            VALUES ({', '.join(placeholders)})
            RETURNING *
        """
        async with pool.acquire() as conn:
            row = await conn.fetchrow(stmt, *values)
            if row:
                d = dict(row)
                d['id'] = str(d['id'])
                d['component_id'] = str(d['component_id'])
                d['pinned_at'] = d['pinned_at'].isoformat() if d['pinned_at'] else None
                d['updated_at'] = d['updated_at'].isoformat() if d['updated_at'] else None
                return d
            return {}

    async def get_pinned_app(self, pin_id: str, tenant_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT p.*, c.name AS component_name, c.status AS component_status
                FROM pinned_apps p
                JOIN components c ON c.id = p.component_id
                WHERE p.id = $1::uuid AND p.tenant_id = $2 AND p.user_id = $3
            """, pin_id, tenant_id, user_id)
            if row:
                d = dict(row)
                d['id'] = str(d['id'])
                d['component_id'] = str(d['component_id'])
                d['pinned_at'] = d['pinned_at'].isoformat() if d['pinned_at'] else None
                d['updated_at'] = d['updated_at'].isoformat() if d['updated_at'] else None
                return d
            return None

    async def list_pinned_apps(self, tenant_id: str, user_id: str) -> List[Dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    p.id, p.tenant_id, p.user_id, p.component_id,
                    p.slot_name, p.description, p.icon, p.sort_order,
                    p.metadata, p.pinned_at, p.updated_at,
                    c.name AS component_name, c.version AS component_version,
                    c.bundle_size_bytes, c.status AS component_status,
                    c.created_at AS component_created_at
                FROM pinned_apps p
                JOIN components c ON c.id = p.component_id
                WHERE p.tenant_id = $1 AND p.user_id = $2
                ORDER BY p.sort_order ASC, p.pinned_at ASC
            """, tenant_id, user_id)
            result = []
            for row in rows:
                d = dict(row)
                d['id'] = str(d['id'])
                d['component_id'] = str(d['component_id'])
                d['pinned_at'] = d['pinned_at'].isoformat() if d['pinned_at'] else None
                d['updated_at'] = d['updated_at'].isoformat() if d['updated_at'] else None
                if d.get('component_created_at'):
                    d['component_created_at'] = d['component_created_at'].isoformat()
                result.append(d)
            return result

    async def update_pinned_app_component(self, pin_id: str, tenant_id: str, user_id: str,
                                          component_id: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            if metadata is not None:
                result = await conn.execute("""
                    UPDATE pinned_apps
                    SET component_id = $1::uuid, metadata = $2, updated_at = NOW()
                    WHERE id = $3::uuid AND tenant_id = $4 AND user_id = $5
                """, component_id, json.dumps(metadata), pin_id, tenant_id, user_id)
            else:
                result = await conn.execute("""
                    UPDATE pinned_apps
                    SET component_id = $1::uuid, updated_at = NOW()
                    WHERE id = $2::uuid AND tenant_id = $3 AND user_id = $4
                """, component_id, pin_id, tenant_id, user_id)
            return "UPDATE 0" not in result

    async def update_pinned_app_meta(self, pin_id: str, tenant_id: str, user_id: str,
                                     updates: Dict[str, Any]) -> bool:
        pool = await self._get_pool()
        allowed = {"slot_name", "description", "icon", "sort_order", "metadata"}
        filtered = {k: v for k, v in updates.items() if k in allowed}
        if not filtered:
            return False
        set_clauses = []
        params: list = []
        for key, val in filtered.items():
            params.append(val)
            set_clauses.append(f"{key} = ${len(params)}")
        params.extend([pin_id, tenant_id, user_id])
        stmt = f"""
            UPDATE pinned_apps
            SET {', '.join(set_clauses)}, updated_at = NOW()
            WHERE id = ${len(params)-2}::uuid
              AND tenant_id = ${len(params)-1}
              AND user_id = ${len(params)}
        """
        async with pool.acquire() as conn:
            result = await conn.execute(stmt, *params)
            return "UPDATE 0" not in result

    async def delete_pinned_app(self, pin_id: str, tenant_id: str, user_id: str) -> bool:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM pinned_apps
                WHERE id = $1::uuid AND tenant_id = $2 AND user_id = $3
            """, pin_id, tenant_id, user_id)
            return "DELETE 0" not in result

    # ------------------------------------------------------------------
    # API Keys — Postgres
    # ------------------------------------------------------------------

    async def create_api_key(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pool = await self._get_pool()
        fields = list(data.keys())
        values = list(data.values())
        placeholders = [f"${i+1}" for i in range(len(values))]
        stmt = f"""
            INSERT INTO api_keys ({', '.join(fields)})
            VALUES ({', '.join(placeholders)})
            RETURNING *
        """
        async with pool.acquire() as conn:
            row = await conn.fetchrow(stmt, *values)
            if row:
                d = dict(row)
                d['id'] = str(d['id'])
                d['created_at'] = d['created_at'].isoformat() if d.get('created_at') else None
                d['last_used_at'] = d['last_used_at'].isoformat() if d.get('last_used_at') else None
                d['revoked_at'] = d['revoked_at'].isoformat() if d.get('revoked_at') else None
                return d
            return {}

    async def get_api_key_by_hash(self, key_hash: str) -> Optional[Dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM api_keys WHERE key_hash = $1 LIMIT 1", key_hash
            )
            if row:
                d = dict(row)
                d['id'] = str(d['id'])
                d['created_at'] = d['created_at'].isoformat() if d.get('created_at') else None
                d['last_used_at'] = d['last_used_at'].isoformat() if d.get('last_used_at') else None
                d['revoked_at'] = d['revoked_at'].isoformat() if d.get('revoked_at') else None
                return d
            return None

    async def list_api_keys(self, tenant_id: str, user_id: str) -> List[Dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, label, key_prefix, scopes, rate_limit_rpm,
                       created_at, last_used_at, revoked_at
                FROM api_keys
                WHERE tenant_id = $1 AND user_id = $2 AND revoked_at IS NULL
                ORDER BY created_at DESC
            """, tenant_id, user_id)
            result = []
            for row in rows:
                d = dict(row)
                d['id'] = str(d['id'])
                d['created_at'] = d['created_at'].isoformat() if d.get('created_at') else None
                d['last_used_at'] = d['last_used_at'].isoformat() if d.get('last_used_at') else None
                d['revoked_at'] = d['revoked_at'].isoformat() if d.get('revoked_at') else None
                result.append(d)
            return result

    async def revoke_api_key(self, key_id: str, tenant_id: str, user_id: str) -> bool:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE api_keys
                SET revoked_at = NOW()
                WHERE id = $1::uuid AND tenant_id = $2 AND user_id = $3
                  AND revoked_at IS NULL
            """, key_id, tenant_id, user_id)
            return "UPDATE 0" not in result

    async def touch_api_key(self, key_id: str):
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE api_keys SET last_used_at = NOW() WHERE id = $1::uuid",
                    key_id
                )
        except Exception:
            pass

    async def write_audit_log(self, entry: Dict[str, Any]):
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO audit_log
                        (tenant_id, user_id, key_id, action, resource_id, ip, status_code, meta)
                    VALUES ($1, $2, $3::uuid, $4, $5, $6, $7, $8::jsonb)
                """,
                    entry.get("tenant_id"), entry.get("user_id"),
                    entry.get("key_id"), entry.get("action"),
                    entry.get("resource_id"), entry.get("ip"),
                    entry.get("status_code"), json.dumps(entry.get("meta", {}))
                )
        except Exception as e:
            logger.warning(f"Audit log write failed: {e}")

    # ------------------------------------------------------------------
    # Dashboard layouts — Postgres
    # ------------------------------------------------------------------

    async def get_dashboard_layout(
        self, tenant_id: str, user_id: str, name: str = "default"
    ) -> Optional[Dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT name, layout, updated_at
                FROM dashboard_layouts
                WHERE tenant_id = $1 AND user_id = $2 AND name = $3
            """, tenant_id, user_id, name)
            if not row:
                return None
            d = dict(row)
            lay = d.get("layout")
            if isinstance(lay, str):
                d["layout"] = json.loads(lay)
            elif lay is None:
                d["layout"] = []
            d["updated_at"] = d["updated_at"].isoformat() if d.get("updated_at") else None
            return d

    async def upsert_dashboard_layout(
        self, tenant_id: str, user_id: str, name: str, layout: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO dashboard_layouts (tenant_id, user_id, name, layout, updated_at)
                VALUES ($1, $2, $3, $4::jsonb, NOW())
                ON CONFLICT (tenant_id, user_id, name)
                DO UPDATE SET layout = EXCLUDED.layout, updated_at = NOW()
            """, tenant_id, user_id, name, json.dumps(layout))
            row = await conn.fetchrow("""
                SELECT name, layout, updated_at FROM dashboard_layouts
                WHERE tenant_id = $1 AND user_id = $2 AND name = $3
            """, tenant_id, user_id, name)
            if not row:
                return {"name": name, "layout": layout, "updated_at": None}
            d = dict(row)
            lay = d.get("layout")
            if isinstance(lay, str):
                d["layout"] = json.loads(lay)
            elif lay is None:
                d["layout"] = []
            d["updated_at"] = d["updated_at"].isoformat() if d.get("updated_at") else None
            return {"name": d["name"], "layout": d["layout"], "updated_at": d["updated_at"]}
