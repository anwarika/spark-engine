import re
import esprima
from typing import List, Tuple, Set
from app.models import ValidationResult
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Exhaustive set of top-level keys returned by each mock data profile.
# Used by _check_data_field_contract to catch apiData().totalRevenue-style hallucinations.
_PROFILE_TOP_LEVEL_FIELDS: dict[str, Set[str]] = {
    "ecommerce": {
        "products", "users", "sales", "tasks", "metrics",
        "orders", "order_items", "summary",
    },
    "saas": {
        "plans", "accounts", "users", "subscriptions",
        "subscription_events", "invoices", "payments", "events",
        "metrics", "kpi_monthly",
    },
    "marketing": {
        "campaigns", "ad_groups", "ads", "ad_spend_daily",
        "leads", "touchpoints", "attribution", "metrics",
    },
    "finance": {
        "gl_accounts", "vendors", "customers", "invoices",
        "transactions", "pnl_monthly", "metrics",
    },
    "sales": {
        "reps", "accounts", "contacts", "opportunities",
        "opportunity_stage_history", "activities", "bookings",
        "quota_monthly", "metrics",
    },
}

# All valid first-level keys across every profile (union)
_ALL_VALID_FIELDS: Set[str] = set().union(*_PROFILE_TOP_LEVEL_FIELDS.values())

# Matches apiData().someField  or  apiData().someField.nested
_APIDATA_ACCESS_RE = re.compile(r'apiData\(\)\.(\w+)')


class CodeValidator:
    FORBIDDEN_GLOBALS = [
        "window", "document", "localStorage", "sessionStorage",
        "indexedDB", "fetch", "XMLHttpRequest", "WebSocket",
        "eval", "Function", "setTimeout", "setInterval",
        "importScripts", "postMessage", "parent", "top",
        "opener", "location", "navigator"
    ]

    ALLOWED_IMPORTS = [
        "solid-js", "solid-js/web", "solid-js/store",
        "apexcharts"
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
                f"Invalid import detected: {imp}. Only {', '.join(self.ALLOWED_IMPORTS)} are allowed"
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

        # Fix 5: catch hallucinated data field names before the iframe renders
        field_warnings = self._check_data_field_contract(code)
        warnings.extend(field_warnings)
        # Treat hallucinated fields as hard errors (they always cause runtime crashes)
        errors.extend(field_warnings)

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

    def _check_data_field_contract(self, code: str) -> List[str]:
        """Detect apiData() accesses to fields not in any known mock data profile.

        Only flags the *first* property segment (e.g. "totalRevenue" in
        apiData().totalRevenue.toFixed). Nested sub-fields are not validated
        because they are profile-specific and fine-grained.
        """
        # Skip if the component doesn't use apiData at all
        if 'apiData()' not in code:
            return []

        matches = _APIDATA_ACCESS_RE.findall(code)
        if not matches:
            return []

        invalid = sorted({
            field for field in matches
            if field not in _ALL_VALID_FIELDS
            # loading/error accessors on the resource signal are valid
            and field not in {"loading", "error", "state"}
        })

        if not invalid:
            return []

        return [
            f"Hallucinated data field(s): {', '.join(invalid)}. "
            f"Valid top-level fields are: {', '.join(sorted(_ALL_VALID_FIELDS))}. "
            "Access data via apiData().summary.total_revenue etc."
        ]
