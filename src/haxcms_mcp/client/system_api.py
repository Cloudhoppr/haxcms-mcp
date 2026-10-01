"""Typed System API endpoint helpers (PLAN Phase 1 T1.6, Phase 2 T2.2).

Header requirements follow the `security:` blocks in `specs/system-spec.yaml` (verified live in
Phase 0/2): login/refresh/logout/connection-settings are open; `sites` (list/info/create/clone/
archive), `status`, `system/version`, `session/user`, and `themes` require bearer +
X-HAXCMS-User-Token; `skeletons` and `skeletons/{name}` require bearer only. Phase 3+ adds the
remaining helpers.
"""

from __future__ import annotations

from typing import Any

from haxcms_mcp.client import HaxcmsClient
from haxcms_mcp.client.envelope import unwrap, unwrap_dict, unwrap_full, unwrap_list
from haxcms_mcp.models.site import SiteList


async def login(client: HaxcmsClient, username: str, password: str) -> dict[str, Any]:
    """POST session/login -> full body `{status, jwt}` (cookies land in the client jar)."""
    response = await client.request(
        "POST",
        client.sys("session/login"),
        json={"username": username, "password": password},
        auth="none",
        no_retry=True,
    )
    return unwrap_full(response)


async def refresh(client: HaxcmsClient) -> dict[str, Any]:
    """GET session/refresh using the cookie jar -> `{status, jwt}` + rotated cookie."""
    response = await client.request(
        "GET", client.sys("session/refresh"), auth="none", no_retry=True
    )
    return unwrap_full(response)


async def logout(client: HaxcmsClient) -> Any:
    """POST session/logout -> "loggedout"."""
    response = await client.request(
        "POST", client.sys("session/logout"), auth="none", no_retry=True
    )
    return unwrap(response)


async def session(client: HaxcmsClient) -> Any:
    """GET session (anonymous probe route; bearer attached when one is held)."""
    response = await client.request("GET", client.sys("session"), auth="bearer")
    return unwrap(response)


async def session_user(client: HaxcmsClient) -> Any:
    """GET session/user -> active user profile (bearer + user token)."""
    response = await client.request("GET", client.sys("session/user"), auth="bearer+user")
    return unwrap(response)


async def status(client: HaxcmsClient) -> Any:
    """GET status -> environment diagnostics (includes the upload limit)."""
    response = await client.request("GET", client.sys("status"), auth="bearer+user")
    return unwrap(response)


async def version(client: HaxcmsClient) -> Any:
    """GET system/version -> installed HAXcms version details."""
    response = await client.request("GET", client.sys("system/version"), auth="bearer+user")
    return unwrap(response)


async def list_sites(client: HaxcmsClient) -> SiteList:
    """GET sites -> typed site listing (bearer + user token; verified fact, Phase 0)."""
    response = await client.request("GET", client.sys("sites"), auth="bearer+user")
    return SiteList.from_api(unwrap(response))


async def site_info(client: HaxcmsClient, site: str) -> dict[str, Any]:
    """GET sites/{name} -> `{id, name, title, description, location, metadata, links}`.

    `metadata.pageCount` is the page count; `links` names every system operation for the site.
    """
    response = await client.request("GET", client.sys(f"sites/{site}"), auth="bearer+user")
    return unwrap_dict(response)


async def create_site(client: HaxcmsClient, payload: dict[str, Any]) -> dict[str, Any]:
    """POST sites -> the created site's first item (JSONOutlineSchemaItem).

    The ACTUAL site name is at `metadata.site.name` — on a duplicate request the server silently
    creates `<name>-1` (Phase 2 probe), so callers must read the name back, not assume it.
    """
    response = await client.request("POST", client.sys("sites"), json=payload, auth="bearer+user")
    return unwrap_dict(response)


async def clone_site(client: HaxcmsClient, site: str) -> dict[str, Any]:
    """POST sites/{name}/clone -> `{detail: "/_sites/<new>", name: "<new>"}` (Phase 2 probe)."""
    response = await client.request(
        "POST",
        client.sys(f"sites/{site}/clone"),
        json={"site": {"name": site}},
        auth="bearer+user",
    )
    return unwrap_dict(response)


async def archive_site(client: HaxcmsClient, site: str) -> dict[str, Any]:
    """POST sites/{name}/archive -> `{name, archivedName, detail: "Site archived"}`."""
    response = await client.request(
        "POST",
        client.sys(f"sites/{site}/archive"),
        json={"site": {"name": site}},
        auth="bearer+user",
    )
    return unwrap_dict(response)


async def list_themes(client: HaxcmsClient) -> list[dict[str, Any]]:
    """GET themes -> LIST of theme records (API-REF §3.5 said "map"; live it is a list)."""
    response = await client.request("GET", client.sys("themes"), auth="bearer+user")
    return unwrap_list(response)


async def list_skeletons(client: HaxcmsClient) -> list[dict[str, Any]]:
    """GET skeletons -> LIST of flat skeleton records (bearer only per spec security block)."""
    response = await client.request("GET", client.sys("skeletons"), auth="bearer")
    return unwrap_list(response)


async def get_skeleton(client: HaxcmsClient, name: str) -> dict[str, Any]:
    """GET skeletons/{name} -> `{meta, site, build, ...}` full skeleton detail (bearer only)."""
    response = await client.request("GET", client.sys(f"skeletons/{name}"), auth="bearer")
    return unwrap_dict(response)
