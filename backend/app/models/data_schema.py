"""Data bridge validation schemas for sample/real data swapping."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class DataBridgeMeta(BaseModel):
    """Metadata for data bridge payloads."""
    profile: Optional[str] = None
    scale: Optional[str] = None
    seed: Optional[int] = None
    data_mode: Literal["sample", "real"] = "sample"
    source: Literal["mock", "api"] = "mock"
    cache_hit: Optional[bool] = None


class DataBridgePayload(BaseModel):
    """Schema for data bridge payload validation."""
    mode: Literal["sample", "real"] = "sample"
    source: Literal["mock", "api"] = "mock"
    data: Dict[str, Any] = Field(default_factory=dict)
    meta: Optional[DataBridgeMeta] = None
    schema_hint: Optional[Dict[str, Any]] = None  # JSON Schema of expected structure


class DataSwapRequest(BaseModel):
    """Request body for POST /components/{id}/data/swap."""
    mode: Literal["sample", "real"] = "sample"
    data: Optional[Dict[str, Any]] = None


def validate_data_shape(data: Dict[str, Any], expected_keys: List[str]) -> Dict[str, Any]:
    """
    Validate that data contains expected top-level keys.
    Returns { valid: bool, missing: List[str], errors: List[str] }.
    """
    if not data or not isinstance(data, dict):
        return {"valid": False, "missing": expected_keys, "errors": ["Data must be a non-empty object"]}

    missing = [k for k in expected_keys if k not in data]
    return {
        "valid": len(missing) == 0,
        "missing": missing,
        "errors": [f"Missing required key: {k}" for k in missing] if missing else [],
    }
