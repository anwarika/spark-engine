"""Spark Component Library - Pre-built templates and primitives for rapid microapp generation."""

from .templates import COMPONENT_TEMPLATES, get_template_by_name, list_templates
from .primitives import SOLIDJS_PRIMITIVES, get_primitive

__all__ = [
    "COMPONENT_TEMPLATES",
    "get_template_by_name",
    "list_templates",
    "SOLIDJS_PRIMITIVES",
    "get_primitive",
]

