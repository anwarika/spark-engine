"""Spark Component Library - Pre-built templates and primitives for rapid microapp generation."""

import logging
import os
import importlib.util
from pathlib import Path

from .templates import COMPONENT_TEMPLATES, ComponentTemplate, get_template_by_name, list_templates
from .primitives import SOLIDJS_PRIMITIVES, get_primitive

logger = logging.getLogger(__name__)


def load_custom_templates(directory: str | None = None) -> int:
    """
    Scan a directory for *.py files that define ComponentTemplate instances
    and merge them into COMPONENT_TEMPLATES.
    Uses CUSTOM_TEMPLATES_DIR env var if directory is not provided.
    Returns the number of templates loaded.
    """
    dir_path = directory or os.environ.get("CUSTOM_TEMPLATES_DIR")
    if not dir_path or not os.path.isdir(dir_path):
        return 0

    count = 0
    for py_file in Path(dir_path).glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                for name in dir(mod):
                    obj = getattr(mod, name)
                    if isinstance(obj, ComponentTemplate):
                        COMPONENT_TEMPLATES[obj.name] = obj
                        count += 1
                        logger.info(f"Loaded custom template: {obj.name} from {py_file.name}")
        except Exception as e:
            logger.warning(f"Failed to load custom template from {py_file}: {e}")

    return count


# Auto-load custom templates on import if CUSTOM_TEMPLATES_DIR is set
load_custom_templates()

__all__ = [
    "COMPONENT_TEMPLATES",
    "get_template_by_name",
    "list_templates",
    "load_custom_templates",
    "SOLIDJS_PRIMITIVES",
    "get_primitive",
]

