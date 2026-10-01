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


async def test_server_lists_the_registered_tools() -> None:
    mcp = build_server(_settings())
    async with Client(mcp) as client:
        tools = await client.list_tools()
    by_name = {t.name: t for t in tools}
    # Phase 1 registers the four session tools (PLAN T1.7); Phase 2 the nine site tools (T2.4).
    assert sorted(by_name) == [
        "archive_site",
        "clone_site",
        "create_site",
        "create_site_from_skeleton",
        "get_server_info",
        "get_site",
        "get_skeleton",
        "list_sites",
        "list_skeletons",
        "list_themes",
        "login",
        "logout",
        "whoami",
    ]

    ann = by_name["get_server_info"].annotations
    assert ann is not None
    assert ann.read_only_hint is True
    assert ann.destructive_hint is False
    assert ann.idempotent_hint is True
    assert ann.open_world_hint is False

    # login/logout are writes to session state but not destructive; whoami is read-only
    for name, read_only in [("login", False), ("logout", False), ("whoami", True)]:
        tool_ann = by_name[name].annotations
        assert tool_ann is not None, name
        assert tool_ann.read_only_hint is read_only, name
        assert tool_ann.destructive_hint is False, name


async def test_site_tool_annotations() -> None:
    """Phase 2 annotation matrix (PLAN §5 + tool inventory): reads, writes, destructive."""
    mcp = build_server(_settings())
    async with Client(mcp) as client:
        tools = await client.list_tools()
    by_name = {t.name: t for t in tools}

    read_only = ["get_site", "list_sites", "list_themes", "list_skeletons", "get_skeleton"]
    for name in read_only:
        tool_ann = by_name[name].annotations
        assert tool_ann is not None, name
        assert tool_ann.read_only_hint is True, name
        assert tool_ann.destructive_hint is False, name

    # creating/cloning repeats produce new sites -> not idempotent
    for name in ["create_site", "create_site_from_skeleton", "clone_site"]:
        tool_ann = by_name[name].annotations
        assert tool_ann is not None, name
        assert tool_ann.read_only_hint is False, name
        assert tool_ann.destructive_hint is False, name
        assert tool_ann.idempotent_hint is False, name

    archive_ann = by_name["archive_site"].annotations
    assert archive_ann is not None
    assert archive_ann.read_only_hint is False
    assert archive_ann.destructive_hint is True


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
    # no credentials configured: the live probe degrades gracefully into *_error fields
    haxcms_info = data["haxcms"]
    assert isinstance(haxcms_info, dict)
    assert haxcms_info["version_error"].startswith("[AUTH_REQUIRED]")
    assert haxcms_info["status_error"].startswith("[AUTH_REQUIRED]")


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
