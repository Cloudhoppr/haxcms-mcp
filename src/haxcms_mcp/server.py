"""FastMCP application assembly for the HAXcms MCP server.

`build_server(settings)` creates the FastMCP app and registers every tool, resource, prompt,
and middleware. Later Phases add their registrations here (PLAN.md Section 2.1).
"""

from __future__ import annotations

import mcp_types
from fastmcp import FastMCP

from haxcms_mcp import __version__
from haxcms_mcp.config import Settings
from haxcms_mcp.middleware import (
    ErrorTranslationMiddleware,
    ReadOnlyMiddleware,
    ToolLoggingMiddleware,
)


def build_server(settings: Settings) -> FastMCP:
    """Create and configure the FastMCP application for one Instance."""
    mcp = FastMCP("haxcms-mcp")

    # Order matters: read-only gate outermost, then logging, then error translation
    # closest to the tool functions.
    mcp.add_middleware(ReadOnlyMiddleware(settings))
    mcp.add_middleware(ToolLoggingMiddleware())
    mcp.add_middleware(ErrorTranslationMiddleware())

    @mcp.tool(
        description=(
            "Return identity and configuration of this HAXcms MCP server. "
            "Use it to check which HAXcms instance the server talks to and whether "
            "Read-Only Mode is active. No HTTP request is made."
        ),
        annotations=mcp_types.ToolAnnotations(
            title="Server info",
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    async def get_server_info() -> dict[str, object]:
        return {
            "name": "haxcms-mcp",
            "version": __version__,
            "base_url": settings.base_url,
            "read_only": settings.read_only,
            "transport": settings.transport,
        }

    return mcp
