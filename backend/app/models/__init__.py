from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
import uuid


class ComponentCreate(BaseModel):
    name: str
    description: str = ""
    solidjs_code: str
    tenant_id: str
    user_id: str


class Component(BaseModel):
    id: uuid.UUID
    tenant_id: str
    user_id: str
    name: str
    description: str
    solidjs_code: str
    code_hash: str
    version: str
    validated: bool
    compiled: bool
    compiled_bundle: Optional[str] = None
    bundle_size_bytes: int
    status: Literal["active", "archived"]
    created_at: datetime
    updated_at: datetime


class ChatMessage(BaseModel):
    session_id: str
    tenant_id: str
    user_id: str
    message: str


class ChatResponse(BaseModel):
    type: Literal["text", "component"]
    content: str
    component_id: Optional[uuid.UUID] = None
    reasoning: str = ""
    # microapp_kind and appsmith_path removed as deprecated


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = []
    warnings: list[str] = []


class CompilationResult(BaseModel):
    success: bool
    bundle: Optional[str] = None
    bundle_size: int = 0
    compile_time_ms: int = 0
    error: Optional[str] = None


class ComponentFeedback(BaseModel):
    component_id: uuid.UUID
    user_id: str
    rating: Literal[1, 5]
    feedback_text: str = ""
