"""
Tests for the Python Data Transform Layer (app/services/transform.py).

Covers:
  - _strip_fences:       markdown fence removal
  - _summarise_schema:   schema summary string generation
  - _extract_result:     output validation
  - execute_transform:   Monty sandbox execution (no LLM)
  - run:                 full pipeline (mocked LLM)
"""
import asyncio
import json
import pytest

from app.services.transform import (
    TransformError,
    TransformService,
    _extract_result,
    _strip_fences,
    _summarise_schema,
)


# ── _strip_fences ─────────────────────────────────────────────────────────────

class TestStripFences:
    def test_no_fences(self):
        code = "result = {'x': 1}"
        assert _strip_fences(code) == code

    def test_python_fences(self):
        code = "```python\nresult = {'x': 1}\n```"
        assert _strip_fences(code) == "result = {'x': 1}"

    def test_plain_fences(self):
        code = "```\nresult = {'x': 1}\n```"
        assert _strip_fences(code) == "result = {'x': 1}"

    def test_fence_only_on_first_line(self):
        # closing fence missing — should still strip opening
        code = "```python\nresult = {'x': 1}"
        assert _strip_fences(code) == "result = {'x': 1}"

    def test_multiline_code_preserved(self):
        code = "```\na = 1\nb = 2\nresult = {'a': a}\n```"
        assert _strip_fences(code) == "a = 1\nb = 2\nresult = {'a': a}"


# ── _summarise_schema ─────────────────────────────────────────────────────────

class TestSummariseSchema:
    def test_scalar_values(self):
        summary = _summarise_schema({"count": 42, "name": "test"})
        assert "count" in summary
        assert "int" in summary
        assert "name" in summary

    def test_list_of_dicts(self):
        data = {"orders": [{"id": 1, "revenue": 100}, {"id": 2, "revenue": 200}]}
        summary = _summarise_schema(data)
        assert "orders" in summary
        assert "2 items" in summary
        assert "id" in summary

    def test_empty_list(self):
        summary = _summarise_schema({"items": []})
        assert "items" in summary
        assert "0 items" in summary

    def test_nested_dict(self):
        summary = _summarise_schema({"meta": {"version": 1, "env": "prod"}})
        assert "meta" in summary
        assert "version" in summary

    def test_empty_data(self):
        assert _summarise_schema({}) == "  (empty)"


# ── _extract_result ───────────────────────────────────────────────────────────

class TestExtractResult:
    def test_valid_dict(self):
        out = _extract_result({"key": [1, 2, 3]}, "code")
        assert out == {"key": [1, 2, 3]}

    def test_not_a_dict_raises(self):
        with pytest.raises(TransformError, match="must be a dict"):
            _extract_result([1, 2, 3], "code")

    def test_empty_dict_raises(self):
        with pytest.raises(TransformError, match="empty dict"):
            _extract_result({}, "code")

    def test_non_serializable_raises(self):
        with pytest.raises(TransformError, match="non-JSON-serializable"):
            _extract_result({"k": object()}, "code")

    def test_nested_valid(self):
        data = {"rows": [{"a": 1}, {"a": 2}], "total": 2}
        assert _extract_result(data, "code") == data


# ── execute_transform (Monty sandbox, no LLM) ─────────────────────────────────

class TestExecuteTransform:
    """
    Tests that exercise only the Monty execution path; no LLM calls.
    We instantiate TransformService but bypass generate_transform_code by
    calling execute_transform directly with pre-written code.
    """

    @pytest.fixture
    def svc(self, monkeypatch):
        """Return a TransformService with LLM init patched out."""
        monkeypatch.setattr(
            "app.services.transform.TransformService.__init__",
            _patched_init,
        )
        s = TransformService.__new__(TransformService)
        _patched_init(s)
        return s

    def _run(self, coro):
        return asyncio.new_event_loop().run_until_complete(coro)

    # ── happy-path cases ──────────────────────────────────────────────────────

    def test_simple_sum(self, svc):
        code = "result = {'total': sum(data['values'])}"
        result, ms = self._run(svc.execute_transform(code, {"values": [10, 20, 30]}))
        assert result == {"total": 60}
        assert ms > 0

    def test_groupby_without_collections(self, svc):
        """Revenue by category using plain dict (our fixed pattern)."""
        code = """
by_cat = {}
for order in data.get('orders', []):
    cat = order.get('category', 'unknown')
    by_cat[cat] = by_cat.get(cat, 0) + order.get('revenue', 0)
result = {'revenue_by_category': by_cat}
"""
        raw = {
            "orders": [
                {"product": "A", "revenue": 100, "category": "tools"},
                {"product": "B", "revenue": 200, "category": "tools"},
                {"product": "C", "revenue": 50,  "category": "misc"},
            ]
        }
        result, _ = self._run(svc.execute_transform(code, raw))
        assert result["revenue_by_category"]["tools"] == 300
        assert result["revenue_by_category"]["misc"] == 50

    def test_stdlib_math_allowed(self, svc):
        code = "import math\nresult = {'pi': math.pi, 'sqrt9': math.sqrt(9)}"
        result, _ = self._run(svc.execute_transform(code, {}))
        assert abs(result["pi"] - 3.14159) < 0.001
        assert result["sqrt9"] == 3.0

    def test_stdlib_re_allowed(self, svc):
        code = """
import re
emails = [e for e in data['items'] if re.match(r'^[\\w.+-]+@[\\w-]+\\.[a-z]{2,}$', e)]
result = {'valid_emails': emails}
"""
        result, _ = self._run(
            svc.execute_transform(code, {"items": ["a@b.com", "not-email", "x@y.org"]})
        )
        assert result["valid_emails"] == ["a@b.com", "x@y.org"]

    def test_top_n_sort(self, svc):
        code = """
rows = data.get('rows', [])
sorted_rows = sorted(rows, key=lambda r: -r['score'])[:3]
result = {'top3': sorted_rows}
"""
        rows = [{"name": chr(65 + i), "score": i * 10} for i in range(10)]
        result, _ = self._run(svc.execute_transform(code, {"rows": rows}))
        assert result["top3"][0]["score"] == 90
        assert len(result["top3"]) == 3

    # ── sandbox security ──────────────────────────────────────────────────────

    def test_collections_not_available(self, svc):
        code = "from collections import defaultdict\nd = defaultdict(int)\nresult = {'x': 1}"
        with pytest.raises(TransformError, match="execution failed"):
            self._run(svc.execute_transform(code, {}))

    def test_no_network_access(self, svc):
        code = "import urllib\nresult = {'x': 1}"
        with pytest.raises(TransformError, match="execution failed"):
            self._run(svc.execute_transform(code, {}))

    def test_no_open_allowed(self, svc):
        code = "f = open('/etc/passwd')\nresult = {'x': 1}"
        with pytest.raises(TransformError, match="execution failed"):
            self._run(svc.execute_transform(code, {}))

    # ── error / validation cases ──────────────────────────────────────────────

    def test_result_not_dict_raises(self, svc):
        code = "result = [1, 2, 3]"
        with pytest.raises(TransformError, match="must be a dict"):
            self._run(svc.execute_transform(code, {}))

    def test_empty_result_raises(self, svc):
        code = "result = {}"
        with pytest.raises(TransformError, match="empty dict"):
            self._run(svc.execute_transform(code, {}))

    def test_oversized_input_raises(self, svc):
        big = {"data": "x" * (11 * 1024 * 1024)}
        with pytest.raises(TransformError, match="10 MB"):
            self._run(svc.execute_transform("result = {'x': 1}", big))

    def test_error_code_attached_on_failure(self, svc):
        bad_code = "result = [1, 2]"
        try:
            self._run(svc.execute_transform(bad_code, {}))
            pytest.fail("Expected TransformError")
        except TransformError as e:
            assert e.code == bad_code


# ── run() with mocked LLM ─────────────────────────────────────────────────────

class TestRunPipeline:
    """Full pipeline test: mock generate_transform_code, verify run() end-to-end."""

    def _run(self, coro):
        return asyncio.new_event_loop().run_until_complete(coro)

    def test_run_returns_result_ms_code(self, monkeypatch):
        svc = TransformService.__new__(TransformService)
        _patched_init(svc)

        generated_code = "result = {'answer': sum(data['nums'])}"

        async def fake_generate(raw_data, description):
            return generated_code

        monkeypatch.setattr(svc, "generate_transform_code", fake_generate)

        result, ms, code = self._run(svc.run({"nums": [1, 2, 3]}, "sum of nums"))
        assert result == {"answer": 6}
        assert ms > 0
        assert code == generated_code

    def test_run_propagates_transform_error(self, monkeypatch):
        svc = TransformService.__new__(TransformService)
        _patched_init(svc)

        async def bad_generate(raw_data, description):
            raise TransformError("LLM down")

        monkeypatch.setattr(svc, "generate_transform_code", bad_generate)

        with pytest.raises(TransformError, match="LLM down"):
            self._run(svc.run({}, "anything"))


# ── helpers ───────────────────────────────────────────────────────────────────

def _patched_init(self):
    """Minimal __init__ that skips LLM gateway setup."""
    from app.services.transform import _monty_available
    self._monty_ok = _monty_available()
    self._gateway = None
    self._llm_call = None
