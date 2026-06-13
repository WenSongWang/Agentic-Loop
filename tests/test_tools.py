from __future__ import annotations

import pytest

from agentic_loop.tools.registry import build_default_registry


@pytest.mark.asyncio
async def test_read_file(tmp_path) -> None:
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    tools = build_default_registry(cwd=tmp_path)
    result = await tools.execute("read_file", '{"path": "a.txt"}')
    assert result == "hello"


@pytest.mark.asyncio
async def test_write_file(tmp_path) -> None:
    tools = build_default_registry(cwd=tmp_path)
    result = await tools.execute("write_file", '{"path": "out.txt", "content": "data"}')
    assert "Wrote" in result
    assert (tmp_path / "out.txt").read_text(encoding="utf-8") == "data"


@pytest.mark.asyncio
async def test_bash_disabled_by_default(tmp_path) -> None:
    tools = build_default_registry(cwd=tmp_path, allow_bash=False)
    result = await tools.execute("bash", '{"command": "echo hi"}')
    assert "disabled" in result


@pytest.mark.asyncio
async def test_bash_when_allowed(tmp_path) -> None:
    tools = build_default_registry(cwd=tmp_path, allow_bash=True)
    result = await tools.execute("bash", '{"command": "echo hi"}')
    assert "hi" in result


@pytest.mark.asyncio
async def test_path_escape_blocked(tmp_path) -> None:
    tools = build_default_registry(cwd=tmp_path)
    result = await tools.execute("read_file", '{"path": "../outside.txt"}')
    assert "Error" in result
