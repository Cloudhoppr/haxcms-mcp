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
    # Phase 1 registers the four session tools (PLAN T1.7); Phase 2 the nine site tools
    # (T2.4); Phase 3 the sixteen outline and page tools (T3.5); Phase 4 the twelve
    # content tools (T4.5) — 41 in total.
    assert sorted(by_name) == [
        "add_block",
        "add_link",
        "archive_site",
        "clone_site",
        "create_page",
        "create_pages",
        "create_site",
        "create_site_from_skeleton",
        "delete_page",
        "get_block_schema",
        "get_outline",
        "get_page",
        "get_page_blocks",
        "get_page_content",
        "get_page_revision",
        "get_server_info",
        "get_site",
        "get_skeleton",
        "list_blocks",
        "list_page_revisions",
        "list_pages",
        "list_sites",
        "list_skeletons",
        "list_tags",
        "list_themes",
        "login",
        "logout",
        "move_block",
        "move_page",
        "normalize_slugs",
        "remove_block",
        "reorder_pages",
        "replace_block",
        "restore_page_revision",
        "search_site",
        "set_block_text",
        "set_page_content",
        "set_page_parent",
        "update_block",
        "update_page_details",
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


async def test_page_tool_annotations() -> None:
    """Phase 3 annotation matrix (PLAN T3.5): reads, repeats-differ writes, destructive."""
    mcp = build_server(_settings())
    async with Client(mcp) as client:
        tools = await client.list_tools()
    by_name = {t.name: t for t in tools}

    read_only = [
        "get_outline",
        "list_pages",
        "get_page",
        "list_page_revisions",
        "get_page_revision",
        "search_site",
        "list_tags",
    ]
    for name in read_only:
        tool_ann = by_name[name].annotations
        assert tool_ann is not None, name
        assert tool_ann.read_only_hint is True, name
        assert tool_ann.destructive_hint is False, name

    # repeating a create makes another page; repeating a move moves again -> not idempotent
    for name in ["create_page", "create_pages", "move_page"]:
        tool_ann = by_name[name].annotations
        assert tool_ann is not None, name
        assert tool_ann.read_only_hint is False, name
        assert tool_ann.destructive_hint is False, name
        assert tool_ann.idempotent_hint is False, name

    # same arguments twice -> same end state, no loss
    for name in ["update_page_details", "set_page_parent", "normalize_slugs"]:
        tool_ann = by_name[name].annotations
        assert tool_ann is not None, name
        assert tool_ann.read_only_hint is False, name
        assert tool_ann.destructive_hint is False, name
        assert tool_ann.idempotent_hint is True, name

    # full-manifest rewrite, page removal and history rollback -> destructive
    for name in ["reorder_pages", "delete_page", "restore_page_revision"]:
        tool_ann = by_name[name].annotations
        assert tool_ann is not None, name
        assert tool_ann.read_only_hint is False, name
        assert tool_ann.destructive_hint is True, name


async def test_content_tool_annotations() -> None:
    """Phase 4 annotation matrix (PLAN T4.5): reads, appends, edits, destructive writes."""
    mcp = build_server(_settings())
    async with Client(mcp) as client:
        tools = await client.list_tools()
    by_name = {t.name: t for t in tools}

    for name in ["get_page_content", "get_page_blocks", "list_blocks", "get_block_schema"]:
        tool_ann = by_name[name].annotations
        assert tool_ann is not None, name
        assert tool_ann.read_only_hint is True, name
        assert tool_ann.destructive_hint is False, name

    # repeating an append adds another block; repeating a link wraps the text again
    for name in ["add_block", "add_link"]:
        tool_ann = by_name[name].annotations
        assert tool_ann is not None, name
        assert tool_ann.read_only_hint is False, name
        assert tool_ann.destructive_hint is False, name
        assert tool_ann.idempotent_hint is False, name

    # same arguments twice -> same end state (re-moved, re-set, re-written)
    for name in ["move_block", "update_block", "set_block_text"]:
        tool_ann = by_name[name].annotations
        assert tool_ann is not None, name
        assert tool_ann.read_only_hint is False, name
        assert tool_ann.destructive_hint is False, name
        assert tool_ann.idempotent_hint is True, name

    # whole-body rewrite, block swap and block removal -> destructive
    for name in ["set_page_content", "replace_block", "remove_block"]:
        tool_ann = by_name[name].annotations
        assert tool_ann is not None, name
        assert tool_ann.read_only_hint is False, name
        assert tool_ann.destructive_hint is True, name


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
