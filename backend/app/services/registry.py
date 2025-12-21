from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from app.database import get_storage
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
        storage = get_storage()
        
        try:
            data = {
                "tenant_id": tenant_id,
                "name": spec.name,
                "description": spec.description,
                "category": spec.category,
                "tags": ["registry", spec.category],
                "solidjs_code": "", 
                "is_public": False
            }
            
            await storage.create_or_update_template(tenant_id, data)
            return True
        except Exception as e:
            logger.error(f"Failed to register component: {e}")
            return False

    async def get_registry_context(self, tenant_id: str) -> str:
        """Get the formatted context string of all registered components for the LLM."""
        storage = get_storage()
        
        try:
            # Fetch templates/components marked as registry items
            # We can use list_component_templates. 
            # Ideally we filter by tag "registry" but the storage list method supports tags.
            result = await storage.list_component_templates(tenant_id, tag="registry")
            
            if not result["templates"]:
                return ""
            
            context = "AVAILABLE CUSTOM COMPONENTS:\n"
            for item in result["templates"]:
                context += f"- <{item['name']} />: {item['description']}\n"
            
            return context
        except Exception as e:
            logger.error(f"Failed to fetch registry context: {e}")
            return ""
