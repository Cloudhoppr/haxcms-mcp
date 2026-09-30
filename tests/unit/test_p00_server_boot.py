"""Unit tests for the Phase 0 server: boot, tool registry, middleware behaviour."""

from __future__ import annotations

import mcp_types
import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

from haxcms_mcp.config import Settings
from haxcms_mcp.errors import ErrorCode, HaxcmsMcpError
from haxcms_mcp.server import build_server

pytestmark = pytest.mark.unit


def _settings(**overrides: object) -> Settings:
    return Settings(base_url="http://localhost:3000", **overrides)  # type: ignore[arg-type]


def _add_fake_write_tool(mcp: FastMCP) -> None:
    @mcp.tool(
        annotations=mcp_types.ToolAnnotations(
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=False,
        )
    )
    async def fake_write(x: int) -> int:
        return x + 1


def _add_fake_error_tool(mcp: FastMCP) -> None:
    @mcp.tool(
        annotations=mcp_types.ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        )
    )
    async def fake_error() -> str:
        raise HaxcmsMcpError(
            ErrorCode.NOT_FOUND, "page 'x' does not exist", hint="call list_pages first"
        )


async def test_server_lists_exactly_get_server_info() -> None:
    mcp = build_server(_settings())
    async with Client(mcp) as client:
        tools = await client.list_tools()
    assert [t.name for t in tools] == ["get_server_info"]
    ann = tools[0].annotations
    assert ann is not None
    assert ann.read_only_hint is True
    assert ann.destructive_hint is False
    assert ann.idempotent_hint is True
    assert ann.open_world_hint is False


async def test_get_server_info_payload() -> None:
    mcp = build_server(_settings(read_only=True))
    async with Client(mcp) as client:
        result = await client.call_tool("get_server_info", {})
    data = result.data
    assert isinstance(data, dict)
    assert data["name"] == "haxcms-mcp"
    assert data["base_url"] == "http://localhost:3000"
    assert data["read_only"] is True
    assert data["transport"] == "stdio"
    assert isinstance(data["version"], str)


async def test_read_only_mode_blocks_write_tool() -> None:
    mcp = build_server(_settings(read_only=True))
    _add_fake_write_tool(mcp)
    async with Client(mcp) as client:
        with pytest.raises(ToolError) as excinfo:
            await client.call_tool("fake_write", {"x": 1})
    assert "[READ_ONLY]" in str(excinfo.value)
    # read-only tool still works
    async with Client(mcp) as client:
        result = await client.call_tool("get_server_info", {})
    assert result.data is not None


async def test_write_tool_allowed_when_not_read_only() -> None:
    mcp = build_server(_settings(read_only=False))
    _add_fake_write_tool(mcp)
    async with Client(mcp) as client:
        result = await client.call_tool("fake_write", {"x": 1})
    assert result.data == 2


async def test_error_middleware_formats_codes() -> None:
    mcp = build_server(_settings())
    _add_fake_error_tool(mcp)
    async with Client(mcp) as client:
        with pytest.raises(ToolError) as excinfo:
            await client.call_tool("fake_error", {})
    assert str(excinfo.value) == "[NOT_FOUND] page 'x' does not exist. call list_pages first"
