"""
Python Data Transform Layer — powered by pydantic-monty.

Enables LLM-generated Python code to safely aggregate and reshape raw integrator
data before it is stored in the Data Bridge and displayed in a Spark component.

Flow:
  1. Integrator sends: raw_data (any shape) + plain-English transform description
  2. LLM generates a short Python script (stdlib-only, deterministic, temperature=0.1)
  3. Monty executes the script in an isolated Rust-based sandbox (microseconds, no I/O)
  4. Result dict is validated (JSON-serializable, non-empty)
  5. Caller stores result in Redis via Data Bridge or returns it directly (preview mode)

Security:
  - Monty sandbox: no filesystem, no env vars, no network, no third-party imports
  - Spark enforces: input ≤ 10 MB, execution ≤ 5 s, output must be a plain dict
  - LLM prompt explicitly forbids eval/exec/open/import beyond stdlib
"""
import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Max size for raw_data payload (bytes of JSON-encoded input)
_MAX_INPUT_BYTES = 10 * 1024 * 1024  # 10 MB
# Monty execution wall-clock limit (seconds)
_EXEC_TIMEOUT_S = 5.0


# ── Transform-specific errors ────────────────────────────────────────────────

class TransformError(Exception):
    """Raised when transform generation or execution fails."""
    def __init__(self, message: str, code: Optional[str] = None):
        super().__init__(message)
        self.code = code  # the generated Python code, if available


# ── System prompt ────────────────────────────────────────────────────────────

_TRANSFORM_SYSTEM_PROMPT = """\
You are a Python data transformation expert working inside a strictly sandboxed environment.

Your job: given a dataset (a Python dict called `data`) and a plain-English description of a
transformation, write minimal Python code that computes the requested result.

RULES (non-negotiable):
1. You may ONLY import from this list: json, datetime, re, math, collections
2. Input is always available as a variable called `data` (already a Python dict — do not parse it)
3. You MUST assign your final output to a variable called `result`
4. `result` MUST be a plain Python dict with JSON-serializable values (str, int, float, list, dict, bool, None)
5. NO file I/O (open, read, write)
6. NO network calls (requests, urllib, http)
7. NO eval, exec, compile, __import__, globals, locals, getattr with dynamic names
8. NO class definitions
9. Keep the code short (< 60 lines). Prefer clarity over cleverness.
10. If the transform is ambiguous or the required data keys are missing from `data`,
    return `result = {"error": "reason here"}` — do NOT raise exceptions.

OUTPUT FORMAT:
Return ONLY the raw Python code. No markdown fences, no explanation, no comments beyond inline ones.

EXAMPLE:
Transform description: "Compute total revenue by product category, top 10"

from collections import defaultdict
by_cat = defaultdict(float)
for order in data.get("orders", []):
    cat = order.get("category", "Unknown")
    by_cat[cat] += order.get("revenue", 0)
result = {
    "revenue_by_category": sorted(
        [{"category": k, "revenue": round(v, 2)} for k, v in by_cat.items()],
        key=lambda x: -x["revenue"]
    )[:10]
}
"""


# ── Monty availability check ─────────────────────────────────────────────────

def _monty_available() -> bool:
    try:
        import pydantic_monty  # noqa: F401
        return True
    except ImportError:
        return False


# ── Service ───────────────────────────────────────────────────────────────────

class TransformService:
    """
    Orchestrates the full transform pipeline:
      generate_transform_code()  — LLM → Python code string
      execute_transform()        — Monty → result dict
      run()                      — combined convenience method
    """

    def __init__(self):
        from app.services.llm import _config_from_settings, _llm_call_with_retry
        from app.services.llm_gateway import LLMGateway

        cfg = _config_from_settings()
        self._gateway = LLMGateway(cfg)
        self._llm_call = _llm_call_with_retry
        self._monty_ok = _monty_available()
        if not self._monty_ok:
            logger.warning(
                "pydantic-monty is not installed. Transform execution will be unavailable. "
                "Install it with: pip install pydantic-monty"
            )

    # ── Step 1: LLM code generation ──────────────────────────────────────────

    async def generate_transform_code(
        self,
        raw_data: Dict[str, Any],
        transform_description: str,
    ) -> str:
        """
        Call the LLM to generate Python transform code.

        Passes a schema summary (top-level keys + sample shapes) rather than the
        full dataset, to keep the LLM prompt small and deterministic.
        """
        schema_summary = _summarise_schema(raw_data)

        messages = [
            {"role": "system", "content": _TRANSFORM_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Transform description: {transform_description}\n\n"
                    f"Available data keys and shapes:\n{schema_summary}\n\n"
                    "Write the Python transform code now:"
                ),
            },
        ]

        try:
            completion = await self._llm_call(
                self._gateway,
                messages,
                temperature=0.1,  # deterministic transforms
                max_tokens=1024,
            )
            code = completion.choices[0].message.content.strip()
            # Strip any accidental markdown fences the LLM adds
            code = _strip_fences(code)
            logger.info(f"Generated transform code ({len(code)} chars)")
            return code
        except Exception as e:
            raise TransformError(f"LLM failed to generate transform code: {e}") from e

    # ── Step 2: Monty execution ───────────────────────────────────────────────

    async def execute_transform(
        self,
        code: str,
        raw_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute Python `code` in the Monty sandbox with `data = raw_data`.

        Returns the value of the `result` variable set by the code.
        Raises TransformError if execution fails or output is invalid.
        """
        if not self._monty_ok:
            raise TransformError(
                "pydantic-monty is not installed. Cannot execute transforms. "
                "Add `pydantic-monty` to requirements.txt and reinstall."
            )

        # Safety: reject oversized input
        raw_json = json.dumps(raw_data)
        if len(raw_json) > _MAX_INPUT_BYTES:
            raise TransformError(
                f"raw_data exceeds 10 MB limit ({len(raw_json):,} bytes). "
                "Trim the dataset before transforming."
            )

        # Wrap code so `data` is injected and `result` is the return value
        wrapped = f"""
import json as _json
data = _json.loads(_raw_json)
{code}
result
"""
        import pydantic_monty

        # Capture log lines emitted by sandbox code
        log_lines: List[str] = []

        def _sandbox_log(msg: str):
            log_lines.append(str(msg))

        monty = pydantic_monty.Monty(
            wrapped,
            inputs=["_raw_json"],
        )

        t0 = time.perf_counter()
        try:
            output = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: monty.run(
                        inputs={"_raw_json": raw_json},
                        external_functions={"log": _sandbox_log},
                    ),
                ),
                timeout=_EXEC_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            raise TransformError(
                f"Transform timed out after {_EXEC_TIMEOUT_S}s. "
                "Simplify the transform or reduce the dataset size.",
                code=code,
            )
        except Exception as e:
            raise TransformError(
                f"Transform execution failed: {e}",
                code=code,
            ) from e

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(f"Transform executed in {elapsed_ms:.1f}ms; sandbox logs: {log_lines}")

        result = _extract_result(output, code)
        return result, elapsed_ms

    # ── Combined convenience entry point ──────────────────────────────────────

    async def run(
        self,
        raw_data: Dict[str, Any],
        transform_description: str,
    ) -> Dict[str, Any]:
        """
        Full pipeline: generate code → execute → return (result, elapsed_ms, code).
        """
        code = await self.generate_transform_code(raw_data, transform_description)
        result, elapsed_ms = await self.execute_transform(code, raw_data)
        return result, elapsed_ms, code


# ── Private helpers ───────────────────────────────────────────────────────────

def _summarise_schema(data: Dict[str, Any], max_sample: int = 3) -> str:
    """
    Build a compact schema summary string from the top-level keys of `data`.
    For lists: show length + first `max_sample` item keys.
    For dicts: show keys.
    For scalars: show type + value.
    """
    lines = []
    for key, value in data.items():
        if isinstance(value, list):
            n = len(value)
            if n > 0 and isinstance(value[0], dict):
                sample_keys = list(value[0].keys())[:10]
                lines.append(f"  {key}: List[dict] ({n} items) — keys: {sample_keys}")
            else:
                lines.append(f"  {key}: List ({n} items)")
        elif isinstance(value, dict):
            lines.append(f"  {key}: dict — keys: {list(value.keys())[:10]}")
        else:
            lines.append(f"  {key}: {type(value).__name__} = {repr(value)[:60]}")
    return "\n".join(lines) if lines else "  (empty)"


def _strip_fences(code: str) -> str:
    """Remove markdown code fences the LLM might accidentally include."""
    lines = code.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_result(output: Any, code: str) -> Dict[str, Any]:
    """
    Validate that the Monty output is a non-empty JSON-serializable dict.
    """
    if not isinstance(output, dict):
        raise TransformError(
            f"`result` must be a dict, got {type(output).__name__}. "
            "Ensure your transform assigns a dict to `result`.",
            code=code,
        )
    if not output:
        raise TransformError(
            "`result` is an empty dict. Ensure your transform produces data.",
            code=code,
        )
    # Verify JSON-serialisability
    try:
        json.dumps(output)
    except (TypeError, ValueError) as e:
        raise TransformError(
            f"`result` contains non-JSON-serializable values: {e}",
            code=code,
        ) from e
    return output
