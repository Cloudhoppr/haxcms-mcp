"""FastMCP application assembly for the HAXcms MCP server.

`build_server(settings)` creates the FastMCP app and registers every tool, resource, prompt,
and middleware. Later Phases add their registrations here (PLAN.md Section 2.1).
"""

from __future__ import annotations

from fastmcp import FastMCP

from haxcms_mcp.client import HaxcmsClient
from haxcms_mcp.config import Settings
from haxcms_mcp.middleware import (
    ErrorTranslationMiddleware,
    ReadOnlyMiddleware,
    ToolLoggingMiddleware,
)
from haxcms_mcp.tools.auth import register_auth_tools
from haxcms_mcp.tools.content import register_content_tools
from haxcms_mcp.tools.outline import register_outline_tools
from haxcms_mcp.tools.pages import register_pages_tools
from haxcms_mcp.tools.sites import register_sites_tools


def build_server(settings: Settings) -> FastMCP:
    """Create and configure the FastMCP application for one Instance."""
    mcp = FastMCP("haxcms-mcp")

    # Order matters: read-only gate outermost, then logging, then error translation
    # closest to the tool functions.
    mcp.add_middleware(ReadOnlyMiddleware(settings))
    mcp.add_middleware(ToolLoggingMiddleware())
    mcp.add_middleware(ErrorTranslationMiddleware())

    client = HaxcmsClient(settings)
    register_auth_tools(mcp, settings, client)
    register_sites_tools(mcp, settings, client)
    register_outline_tools(mcp, settings, client)
    register_pages_tools(mcp, settings, client)
    register_content_tools(mcp, settings, client)

    return mcp
