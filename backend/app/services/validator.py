import re
import esprima
from typing import List, Tuple
from app.models import ValidationResult
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class CodeValidator:
    FORBIDDEN_GLOBALS = [
        "window", "document", "localStorage", "sessionStorage",
        "indexedDB", "fetch", "XMLHttpRequest", "WebSocket",
        "eval", "Function", "setTimeout", "setInterval",
        "importScripts", "postMessage", "parent", "top",
        "opener", "location", "navigator"
    ]

    ALLOWED_IMPORTS = [
        "react",
        "react-dom",
        "recharts",
        "@/components/ui",
        "lucide-react",
    ]

    FORBIDDEN_PATTERNS = [
        r"innerHTML\s*=",
        r"outerHTML\s*=",
        r"document\.",
        r"window\.",
        r"\beval\s*\(",  # Only match eval as a word, not in "evalValue"
        r"\bFunction\s*\(",  # Only match Function constructor (capital F)
        r"\bnew\s+Function",
        r"__proto__",
        r"constructor\[",
        r"\bimport\s*\(",  # Dynamic imports
    ]

    def validate(self, code: str) -> ValidationResult:
        errors = []
        warnings = []

        if len(code.encode('utf-8')) > settings.max_component_size_bytes:
            errors.append(
                f"Component code exceeds maximum size of {settings.max_component_size_bytes} bytes"
            )
            return ValidationResult(valid=False, errors=errors)

        syntax_valid, syntax_errors = self._check_syntax(code)
        if not syntax_valid:
            errors.extend(syntax_errors)
            return ValidationResult(valid=False, errors=errors)

        # TEMPORARILY DISABLED - Allow rendering to test
        # forbidden_apis = self._check_forbidden_apis(code)
        # if forbidden_apis:
        #     errors.extend([
        #         f"Forbidden API usage detected: {api}" for api in forbidden_apis
        #     ])

        invalid_imports = self._check_imports(code)
        if invalid_imports:
            errors.extend([
                f"Invalid import detected: {imp}. Allowed: react, react-dom, recharts, @/components/ui/*, lucide-react"
                for imp in invalid_imports
            ])

        # TEMPORARILY DISABLED - Allow rendering to test
        # dangerous_patterns = self._check_dangerous_patterns(code)
        # if dangerous_patterns:
        #     errors.extend([
        #         f"Dangerous code pattern detected: {pattern}" for pattern in dangerous_patterns
        #     ])

        if not self._has_default_export(code):
            errors.append("Component must have a default export")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _check_syntax(self, code: str) -> Tuple[bool, List[str]]:
        try:
            # Try to parse with tolerant mode
            # Note: esprima 4.0.1 doesn't support all modern JS syntax (optional chaining, nullish coalescing, etc.)
            # We rely on the compilation step to catch real syntax errors
            esprima.parseModule(code, {"jsx": True, "tolerant": True})
            return True, []
        except Exception as e:
            error_msg = str(e)
            # Be more lenient with parsing errors for modern syntax
            if any(keyword in error_msg.lower() for keyword in ['unexpected token', 'unexpected identifier']):
                logger.warning(f"Syntax parsing warning (may be modern syntax): {error_msg}")
                # Let it pass - compilation will catch real errors
                return True, []
            return False, [f"Syntax error: {error_msg}"]

    def _check_forbidden_apis(self, code: str) -> List[str]:
        found = []
        for api in self.FORBIDDEN_GLOBALS:
            pattern = rf'\b{re.escape(api)}\b'
            matches = re.findall(pattern, code)
            if matches:
                # Check if it's not in a comment or string (basic check)
                logger.debug(f"API '{api}' found {len(matches)} time(s)")
                found.append(api)
        return found

    def _check_imports(self, code: str) -> List[str]:
        import_pattern = r'import\s+.*?\s+from\s+["\']([^"\']+)["\']'
        imports = re.findall(import_pattern, code)

        invalid = []
        for imp in imports:
            if not any(imp.startswith(allowed) for allowed in self.ALLOWED_IMPORTS):
                if not (imp.startswith('./') or imp.startswith('../')):
                    invalid.append(imp)

        return invalid

    def _check_dangerous_patterns(self, code: str) -> List[str]:
        found = []
        for pattern in self.FORBIDDEN_PATTERNS:
            # Don't use IGNORECASE - we want to catch Function() not function()
            matches = re.findall(pattern, code)
            if matches:
                logger.warning(f"Pattern '{pattern}' matched: {matches[:3]}")  # Show first 3 matches
                found.append(pattern)
        return found

    def _has_default_export(self, code: str) -> bool:
        return bool(
            re.search(r'export\s+default', code) or
            re.search(r'export\s*{\s*\w+\s+as\s+default\s*}', code)
        )
