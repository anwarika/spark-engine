from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any, List
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
    component_id: Optional[str] = None  # When set, iterate on existing component
    mode: Optional[str] = None          # 'dashboard' | 'widget' | 'quick' | None (auto-detect)


class ChatResponse(BaseModel):
    type: Literal["text", "component"]
    content: str
    component_id: Optional[uuid.UUID] = None
    reasoning: str = ""
    meta: Dict[str, Any] = {}  # carries resolved mode, sizing hints, etc.
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


# ------------------------------------------------------------------
# Pinned Apps
# ------------------------------------------------------------------

class PinAppRequest(BaseModel):
    component_id: uuid.UUID
    slot_name: str = Field(..., min_length=1, max_length=120,
                           description="User-visible label shown in the nav bar")
    description: str = ""
    icon: str = ""
    sort_order: int = 0
    metadata: Dict[str, Any] = {}


class UpdatePinMetaRequest(BaseModel):
    slot_name: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class UpdatePinComponentRequest(BaseModel):
    """Re-generate the component under this pin using a new or existing prompt."""
    prompt: Optional[str] = Field(None, description="New generation prompt. If omitted, re-uses the prompt stored in the existing component.")
    data_context: Optional[Dict[str, Any]] = None
    style_context: Optional[Dict[str, Any]] = None


class PinnedAppResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    component_id: str
    slot_name: str
    description: str
    icon: str
    sort_order: int
    metadata: Dict[str, Any]
    pinned_at: Optional[str]
    updated_at: Optional[str]
    # Joined component fields
    component_name: Optional[str] = None
    component_version: Optional[str] = None
    component_status: Optional[str] = None
    iframe_url: Optional[str] = None


# ------------------------------------------------------------------
# Dashboard canvas layout (grid items keyed by pin_id in field `i`)
# ------------------------------------------------------------------

class DashboardLayoutSaveRequest(BaseModel):
    """Persist react-grid-layout items; each item uses `i` = pinned_apps.id."""
    name: str = "default"
    layout: List[Dict[str, Any]]
