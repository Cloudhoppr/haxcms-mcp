"""Typed Site API endpoint helpers (PLAN Phase 2 T2.2).

The three routes below are PUBLIC reads: `specs/site-spec.yaml` sets `security: []` globally
(line 47) and the Phase 2 probe confirmed anonymous 200s for `GET site`, `GET themes`, and
`GET themes/active` — so they use `auth="none"` and never touch the auth manager. Phase 3+ adds
the item/content helpers (which DO require bearer + site token).
"""

from __future__ import annotations

from typing import Any

from haxcms_mcp.client import HaxcmsClient
from haxcms_mcp.client.envelope import unwrap_dict


async def site_summary(client: HaxcmsClient, site: str) -> dict[str, Any]:
    """GET site -> public SiteSummary `{id, name, title, ..., counts, links}`."""
    response = await client.request("GET", client.site_path(site, "site"), auth="none")
    return unwrap_dict(response)


async def list_site_themes(client: HaxcmsClient, site: str) -> dict[str, Any]:
    """GET themes -> ThemeCollection `{count, total, page, themes: [...]}` (public)."""
    response = await client.request("GET", client.site_path(site, "themes"), auth="none")
    return unwrap_dict(response)


async def active_theme(client: HaxcmsClient, site: str) -> dict[str, Any]:
    """GET themes/active -> the site's active theme record (public)."""
    response = await client.request("GET", client.site_path(site, "themes/active"), auth="none")
    return unwrap_dict(response)
