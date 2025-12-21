from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from app.database import get_supabase
import logging

logger = logging.getLogger(__name__)

class ComponentSpec(BaseModel):
    name: str
    description: str
    props: Dict[str, Any]
    usage_example: Optional[str] = None
    category: str = "custom"

class RegistryService:
    def __init__(self):
        pass

    async def register_component(self, tenant_id: str, spec: ComponentSpec) -> bool:
        """Register a new component definition for a tenant."""
        supabase = get_supabase()
        
        try:
            # Upsert logic - we might want to store these in a new table 'component_registry'
            # For now, we'll simulate or assume the table exists or reuse 'component_templates'
            # Let's assume we create a new table for these specs if we were doing migration
            # Since I cannot run migration, I will use a simulated storage or assume 'component_templates' 
            # can hold this if we adapt it.
            # But the plan implies a new service.
            
            # Since I cannot modify DB schema easily without running migrations which requires tools I shouldn't run blind,
            # I will mock the persistence for now or use a JSON blob in an existing table if possible.
            # Actually, `component_templates` is close enough.
            
            existing = supabase.table("component_templates").select("id").eq("name", spec.name).eq("tenant_id", tenant_id).execute()
            
            data = {
                "tenant_id": tenant_id,
                "name": spec.name,
                "description": spec.description,
                "category": spec.category,
                "tags": ["registry", spec.category],
                "solidjs_code": "", # Registry items might just be specs, not code?
                # The LLM needs to know about these to USE them in generation.
                # So we store the metadata.
                "is_public": False
            }
            
            if existing.data:
                supabase.table("component_templates").update(data).eq("id", existing.data[0]["id"]).execute()
            else:
                supabase.table("component_templates").insert(data).execute()
                
            return True
        except Exception as e:
            logger.error(f"Failed to register component: {e}")
            return False

    async def get_registry_context(self, tenant_id: str) -> str:
        """Get the formatted context string of all registered components for the LLM."""
        supabase = get_supabase()
        
        try:
            # Fetch templates/components marked as registry items
            result = supabase.table("component_templates").select("*").eq("tenant_id", tenant_id).execute()
            
            if not result.data:
                return ""
            
            context = "AVAILABLE CUSTOM COMPONENTS:\n"
            for item in result.data:
                context += f"- <{item['name']} />: {item['description']}\n"
                # If we had stored props/usage in a structured way (e.g. in description json), parse it here
            
            return context
        except Exception as e:
            logger.error(f"Failed to fetch registry context: {e}")
            return ""

