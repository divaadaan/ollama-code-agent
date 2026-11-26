"""
Toolkit benchmark: call each of the agent's tools on a known input, check the output, and time it.

Every case names a tool, its arguments and a check on what the tool returned. A case passes when the check holds,
fails when it doesn't, and is an error when the tool raises. Tools often report problems as an error string or an
``{"status": "error"}`` dict instead of raising, so the checks look at the content, not just for an exception.
A case is skipped when its tool isn't loaded (the hosted tools need API keys) or when it needs the network and
``include_network`` is off.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

DEFAULT_TEST_DIR = Path(__file__).parent / "test"
CATEGORIES = ("search", "web", "file", "media")


@dataclass(frozen=True)
class ToolCase:
    category: str
    tool: str
    label: str
    kwargs: Dict[str, Any]
    check: Callable[[Any], bool]
    needs_network: bool = False


def _text(result: Any) -> str:
    """The part of a tool's output worth checking, lower-cased."""
    if isinstance(result, dict):
        if result.get("status") == "error":
            return ""
        result = result.get("content", result)
    return str(result).lower()


def contains(*needles: str) -> Callable[[Any], bool]:
    def check(result: Any) -> bool:
        text = _text(result)
        return all(n.lower() in text for n in needles)

    return check


def downloaded(result: Any) -> bool:
    return isinstance(result, dict) and bool(result.get("path")) and Path(result["path"]).exists()


def not_an_error(result: Any) -> bool:
    text = _text(result).strip()
    return bool(text) and not text.startswith("error")


def default_cases(test_dir: Path = DEFAULT_TEST_DIR) -> List[ToolCase]:
    d = test_dir
    return [
        ToolCase("search", "web_search", "query", {"query": "Python programming language"}, contains("python"), True),
        ToolCase("search", "wikipedia_search", "article", {"query": "Python (programming language)"},
                 contains("python"), True),
        ToolCase("web", "visit_webpage", "example.com", {"url": "https://example.com"}, contains("example domain"),
                 True),
        ToolCase("web", "web_scrape", "example.com", {"url": "https://example.com"}, contains("example domain"), True),
        ToolCase("file", "file_download", "example.com", {"url": "https://example.com"}, downloaded, True),
        ToolCase("file", "file_reader", "text", {"file_path": str(d / "sample.txt")}, contains("quick brown fox")),
        ToolCase("file", "file_reader", "csv", {"file_path": str(d / "test_data.csv")},
                 contains("3 rows", "name, age, joined")),
        ToolCase("file", "file_reader", "json", {"file_path": str(d / "test_data.json")}, contains('"file_reader"')),
        ToolCase("file", "file_reader", "pdf", {"file_path": str(d / "sample.pdf")}, contains("agents read pdf")),
        ToolCase("media", "extract_text_ocr", "png", {"image_path": str(d / "test_image.png")},
                 contains("hello", "agent")),
        ToolCase("media", "image_to_text", "png", {"file_path": str(d / "test_image.png")}, not_an_error, True),
    ]


class ToolkitTester:
    def __init__(
        self,
        tools: Union[Dict[str, Any], List[Any]],
        test_data_dir: Union[str, Path] = DEFAULT_TEST_DIR,
        include_network: bool = True,
        cases: Optional[List[ToolCase]] = None,
    ):
        # smolagents keeps an agent's tools in a dict keyed by name; get_default_tools() returns a list.
        self.tools = dict(tools) if isinstance(tools, dict) else {t.name: t for t in tools}
        self.test_data_dir = Path(test_data_dir)
        self.include_network = include_network
        self.cases = cases if cases is not None else default_cases(self.test_data_dir)
        self.results: Dict[str, List[Dict[str, Any]]] = {}

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run every case, one at a time, grouped by category."""
        self.results = {}
        for category in CATEGORIES:
            cases = [c for c in self.cases if c.category == category]
            if cases:
                self.results[category] = [await asyncio.to_thread(self._run_case, c) for c in cases]
        return self.results

    def test_search_tools(self) -> List[Dict[str, Any]]:
        """Web search and Wikipedia."""
        return self._run_category("search")

    def test_web_tools(self) -> List[Dict[str, Any]]:
        """Page visits and scraping."""
        return self._run_category("web")

    def test_file_tools(self) -> List[Dict[str, Any]]:
        """Downloading and reading text, CSV, JSON and PDF files."""
        return self._run_category("file")

    def test_media_tools(self) -> List[Dict[str, Any]]:
        """OCR and image description (speech-to-text has no fixture yet)."""
        return self._run_category("media")

    def generate_summary(self) -> Dict[str, Any]:
        """Counts by status, total time, and the cases that didn't pass."""
        rows = [r for rs in self.results.values() for r in rs]
        counts = {s: sum(r["status"] == s for r in rows) for s in ("pass", "fail", "error", "skipped")}
        problems = [f"{r['tool']} ({r['case']}): {r['status']}" for r in rows if r["status"] in ("fail", "error")]
        return {
            "total": len(rows),
            **counts,
            "seconds": round(sum(r["seconds"] for r in rows), 3),
            "problems": problems,
        }

    def _run_category(self, category: str) -> List[Dict[str, Any]]:
        results = [self._run_case(c) for c in self.cases if c.category == category]
        self.results[category] = results
        return results

    def _run_case(self, case: ToolCase) -> Dict[str, Any]:
        tool = self.tools.get(case.tool)
        if tool is None:
            return self._row(case, "skipped", 0.0, "tool not loaded (hosted tools need an API key)")
        if case.needs_network and not self.include_network:
            return self._row(case, "skipped", 0.0, "needs the network")
        return self._benchmark_tool(tool, case)

    def _benchmark_tool(self, tool: Any, case: ToolCase) -> Dict[str, Any]:
        """Run one case with timing and error handling."""
        start = time.perf_counter()
        try:
            result = tool.forward(**case.kwargs)
        except Exception as e:  # a tool that raises is an error, not a crash of the whole benchmark
            logger.warning(f"Tool {case.tool} raised on {case.label}: {e}")
            return self._row(case, "error", time.perf_counter() - start, f"{type(e).__name__}: {e}")
        seconds = time.perf_counter() - start
        try:
            passed = bool(case.check(result))
        except Exception as e:
            return self._row(case, "error", seconds, f"check failed: {type(e).__name__}: {e}")
        return self._row(case, "pass" if passed else "fail", seconds, str(result)[:200])

    @staticmethod
    def _row(case: ToolCase, status: str, seconds: float, detail: str) -> Dict[str, Any]:
        return {
            "tool": case.tool,
            "case": case.label,
            "status": status,
            "seconds": round(seconds, 3),
            "detail": detail,
        }
