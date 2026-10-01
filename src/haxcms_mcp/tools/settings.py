"""Site settings tools (PLAN Phase 6 T6.6).

Read the full settings view (public site.json manifest) and write the settings groups
HAXcms NodeJS 26.8.1 exposes: site info, author, theme, regions, SEO, editor audience,
allowed blocks, platform feature flags, alternative formats. All mutations are bearer +
site token; each upstream route has its own feature gate (a disabled gate surfaces as
FEATURE_DISABLED). `configure_site_git` documents the UNSUPPORTED git publishing block.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from haxcms_mcp.client import HaxcmsClient
from haxcms_mcp.config import Settings
from haxcms_mcp.models.common import dump_model
from haxcms_mcp.services import settings as settings_service
from haxcms_mcp.tools._common import resolve_site, tool_annotations


def register_settings_tools(mcp: FastMCP, settings: Settings, client: HaxcmsClient) -> None:
    """Register the Phase 6 settings tools on the FastMCP app."""

    @mcp.tool(annotations=tool_annotations("Configure site git"))
    async def configure_site_git(
        branch: str | None = None,
        auto_push: bool | None = None,
        remote_url: str | None = None,
        vendor: str | None = None,
        site: str | None = None,
    ) -> dict[str, Any]:
        """Configure the site's git publishing settings — ALWAYS fails UNSUPPORTED.

        HAXcms NodeJS 26.8.1 exposes no API route that persists `metadata.site.git`
        (branch, autoPush, remote url, vendor): the reachable scoped manifest route
        writes only title/homePageId/sw/forceUpgrade, and the full form route needs a
        form token no reachable endpoint mints. The Operator must edit
        `metadata.site.git` in the site's site.json on the server directly.
        get_site_settings still REPORTS the current git block (read-only).
        """
        name = resolve_site(site, settings.default_site)
        result = await settings_service.configure_site_git(
            client,
            name,
            branch=branch,
            auto_push=auto_push,
            remote_url=remote_url,
            vendor=vendor,
        )
        return dump_model(result)
