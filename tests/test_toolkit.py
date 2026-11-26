import asyncio
from pathlib import Path

from core.test_toolkit import ToolCase, ToolkitTester, contains, default_cases
from core.tools import FileReaderTool


class FakeTool:
    def __init__(self, name, result=None, raises=None):
        self.name = name
        self.result = result
        self.raises = raises
        self.calls = []

    def forward(self, **kwargs):
        self.calls.append(kwargs)
        if self.raises:
            raise self.raises
        return self.result


def run(tester):
    return asyncio.run(tester.run_all_tests())


def test_statuses_and_summary():
    tools = [
        FakeTool("good", "the answer is 42"),
        FakeTool("wrong", "no idea"),
        FakeTool("broken", raises=RuntimeError("boom")),
        FakeTool("online", "the answer is 42"),
        FakeTool("quiet_error", {"status": "error", "content": "the answer is 42"}),
    ]
    cases = [
        ToolCase("file", "good", "ok", {}, contains("42")),
        ToolCase("file", "wrong", "miss", {}, contains("42")),
        ToolCase("file", "broken", "raises", {}, contains("42")),
        ToolCase("file", "absent", "not loaded", {}, contains("42")),
        ToolCase("web", "online", "offline run", {}, contains("42"), needs_network=True),
        ToolCase("file", "quiet_error", "error dict", {}, contains("42")),
    ]
    tester = ToolkitTester(tools, include_network=False, cases=cases)
    results = run(tester)
    statuses = {r["case"]: r["status"] for rs in results.values() for r in rs}
    assert statuses == {
        "ok": "pass",
        "miss": "fail",
        "raises": "error",
        "not loaded": "skipped",
        "offline run": "skipped",
        "error dict": "fail",
    }
    summary = tester.generate_summary()
    assert (summary["total"], summary["pass"], summary["fail"], summary["error"], summary["skipped"]) == (6, 1, 2, 1, 2)
    assert "broken (raises): error" in summary["problems"]
    assert tools[3].calls == []  # network case never ran


def test_accepts_the_agent_tool_dict():
    tool = FakeTool("good", "42")
    tester = ToolkitTester({"good": tool}, cases=[ToolCase("file", "good", "ok", {}, contains("42"))])
    assert tester.test_file_tools()[0]["status"] == "pass"


def test_default_file_cases_pass_against_the_real_reader(fixtures_dir):
    cases = [c for c in default_cases(fixtures_dir) if c.tool == "file_reader"]
    assert {c.label for c in cases} == {"text", "csv", "json", "pdf"}
    tester = ToolkitTester([FileReaderTool()], cases=cases)
    rows = tester.test_file_tools()
    assert [r["status"] for r in rows] == ["pass"] * 4


def test_every_default_case_has_its_fixture(fixtures_dir):
    for case in default_cases(fixtures_dir):
        for key in ("file_path", "image_path"):
            if key in case.kwargs:
                assert Path(case.kwargs[key]).exists(), case.kwargs[key]
