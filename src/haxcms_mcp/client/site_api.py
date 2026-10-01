"""Typed Site API endpoint helpers (PLAN Phase 2 T2.2, Phase 3 T3.2).

Auth per `specs/site-spec.yaml` `security:` blocks (source of truth — API-REF §2.6 was wrong
once already):

* PUBLIC reads (`security: []` global, line 47): `GET site`, `GET themes`, `GET themes/active`,
  `GET items`, `GET items/{idOrSlug}`, `GET search`, `GET tags` — confirmed anonymous 200s in
  the Phase 2 probe. The item/search/tags reads are sent with `auth="bearer"` anyway: the
  routes upgrade visibility for authenticated callers (unpublished items; verified in
  siteRouteUtils.filterItemsForAnonymousAccess).
* bearer + SITE token: `POST items`, `PATCH items/{idOrSlug}`, `DELETE items/{idOrSlug}`,
  `PATCH site/outline`, `POST site/normalize-slugs`, and all three revision routes.

Live facts these helpers encode (Phase 3 source reads, recorded in PROGRESS.md):

* `GET items` paginates: default `page.limit` 25, max 200 — callers must paginate.
* `{idOrSlug}` routes are single-segment Express params and the server `decodeURIComponent`s
  them, so nested slugs (which contain `/`) travel percent-encoded (`quote(..., safe="")`).
* `PATCH items/{idOrSlug}` takes `{site:{name}, operation, ...fields}`, ONE operation per
  request; the response `data` is the updated item (summary shape).
* `POST items` single form: `{site:{name}, node:{id,title,location,duplicate,contents},
  parent, order, indent, description, metadata}`; bulk form: `{site:{name}, items:[...]}`
  (response `data` is the LAST created item — createNode.js).
* revisions `{revisionId}` must be a 7-64 hex git hash; restore needs no body.
* `POST site/normalize-slugs` accepts `preview: true` in the body (no writes, returns the
  planned changes); response `data = {changed, preview, changes, skipped}`.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from haxcms_mcp.client import HaxcmsClient
from haxcms_mcp.client.envelope import unwrap_dict

# --- Phase 2: public site-level reads -------------------------------------------------


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


# --- Phase 3: items / outline ----------------------------------------------------------


def _item_path(client: HaxcmsClient, site: str, id_or_slug: str, suffix: str = "") -> str:
    """`items/{quoted}` (+suffix) — slugs may contain `/`, so percent-encode the segment."""
    segment = quote(id_or_slug, safe="")
    tail = f"/{suffix.lstrip('/')}" if suffix else ""
    return client.site_path(site, f"items/{segment}{tail}")


async def list_items(
    client: HaxcmsClient, site: str, *, params: dict[str, Any] | None = None
) -> dict[str, Any]:
    """GET items -> ItemCollection `{count, total, page, items}`.

    `params` carries the raw query keys (`filter.parent`, `page.limit`, `include`, ...).
    Bearer-authenticated: unpublished items are included.
    """
    response = await client.request(
        "GET", client.site_path(site, "items"), params=params, auth="bearer"
    )
    return unwrap_dict(response)


async def get_item(
    client: HaxcmsClient, site: str, id_or_slug: str, *, include_content: bool = False
) -> dict[str, Any]:
    """GET items/{idOrSlug} -> one item record (404 -> NOT_FOUND; bearer sees unpublished)."""
    params = {"include": "content"} if include_content else None
    response = await client.request(
        "GET", _item_path(client, site, id_or_slug), params=params, auth="bearer"
    )
    return unwrap_dict(response)


async def create_item(client: HaxcmsClient, site: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST items (single `node` form or bulk `items` form) -> the created item (bulk: the
    LAST created item — read createNode.js; callers that need every id supply their own)."""
    response = await client.request(
        "POST", client.site_path(site, "items"), json=payload, auth="bearer+site", site=site
    )
    return unwrap_dict(response)


async def update_item(
    client: HaxcmsClient, site: str, id_or_slug: str, operation: str, **fields: Any
) -> dict[str, Any]:
    """PATCH items/{idOrSlug} with ONE nodeDetailOperation -> the updated item record."""
    body: dict[str, Any] = {"site": {"name": site}, "operation": operation, **fields}
    response = await client.request(
        "PATCH", _item_path(client, site, id_or_slug), json=body, auth="bearer+site", site=site
    )
    return unwrap_dict(response)


async def delete_item(client: HaxcmsClient, site: str, id_or_slug: str) -> dict[str, Any]:
    """DELETE items/{idOrSlug} -> the deleted item record (children re-parent to the root)."""
    response = await client.request(
        "DELETE",
        _item_path(client, site, id_or_slug),
        json={"site": {"name": site}},
        auth="bearer+site",
        site=site,
    )
    return unwrap_dict(response)


async def save_outline(
    client: HaxcmsClient, site: str, items: list[dict[str, Any]]
) -> dict[str, Any]:
    """PATCH site/outline -> `{items: [...]}` (the FULL manifest after the save).

    Items omitted from `items` are NOT deleted (saveOutline.js: only an explicit
    `delete: true` entry removes a page) but they also keep their old order — send the
    complete list. Unknown ids are created with server-assigned ids.
    """
    response = await client.request(
        "PATCH",
        client.site_path(site, "site/outline"),
        json={"site": {"name": site}, "items": items},
        auth="bearer+site",
        site=site,
    )
    return unwrap_dict(response)


async def normalize_slugs(
    client: HaxcmsClient, site: str, *, preview: bool = False
) -> dict[str, Any]:
    """POST site/normalize-slugs -> `{changed, preview, changes, skipped}`.

    Regenerates every slug from its title per Pathauto; items with
    `metadata.overridePathauto` land in `skipped`. `preview=True` plans without writing.
    """
    response = await client.request(
        "POST",
        client.site_path(site, "site/normalize-slugs"),
        json={"site": {"name": site}, "preview": preview},
        auth="bearer+site",
        site=site,
    )
    return unwrap_dict(response)


# --- Phase 3: revisions -----------------------------------------------------------------


async def list_revisions(
    client: HaxcmsClient, site: str, id_or_slug: str, *, limit: int = 25, offset: int = 0
) -> dict[str, Any]:
    """GET items/{idOrSlug}/revisions -> `{nodeId, ..., count, total, revisions: [...]}`."""
    response = await client.request(
        "GET",
        _item_path(client, site, id_or_slug, "revisions"),
        params={"page.limit": limit, "page.offset": offset},
        auth="bearer+site",
        site=site,
    )
    return unwrap_dict(response)


async def get_revision(
    client: HaxcmsClient, site: str, id_or_slug: str, revision_id: str
) -> dict[str, Any]:
    """GET items/{idOrSlug}/revisions/{hash} -> `{nodeId, ..., revision, content}`."""
    response = await client.request(
        "GET",
        _item_path(client, site, id_or_slug, f"revisions/{quote(revision_id, safe='')}"),
        auth="bearer+site",
        site=site,
    )
    return unwrap_dict(response)


async def restore_revision(
    client: HaxcmsClient, site: str, id_or_slug: str, revision_id: str
) -> dict[str, Any]:
    """POST items/{idOrSlug}/revisions/{hash}/restore -> `{nodeId, restoredFromHash, ...}`."""
    response = await client.request(
        "POST",
        _item_path(client, site, id_or_slug, f"revisions/{quote(revision_id, safe='')}/restore"),
        json={"site": {"name": site}},
        auth="bearer+site",
        site=site,
    )
    return unwrap_dict(response)


# --- Phase 3: search and tags --------------------------------------------------------------


async def search(
    client: HaxcmsClient, site: str, q: str, *, params: dict[str, Any] | None = None
) -> dict[str, Any]:
    """GET search?q=... -> `{count, total, page, results: [...]}` (400 when q is empty)."""
    query: dict[str, Any] = {"q": q, **(params or {})}
    response = await client.request(
        "GET", client.site_path(site, "search"), params=query, auth="bearer"
    )
    return unwrap_dict(response)


async def list_tags(client: HaxcmsClient, site: str) -> dict[str, Any]:
    """GET tags -> `{count, total, page, tags: [{tag, count}]}` sorted by -count."""
    response = await client.request("GET", client.site_path(site, "tags"), auth="bearer")
    return unwrap_dict(response)


# --- Phase 4: content ---------------------------------------------------------------------


def _content_path(client: HaxcmsClient, site: str, id_or_slug: str) -> str:
    segment = quote(id_or_slug, safe="")  # nested slugs contain `/`
    return client.site_path(site, f"content/{segment}")


async def get_content(
    client: HaxcmsClient, site: str, id_or_slug: str, *, fmt: str = "json"
) -> dict[str, Any]:
    """GET content/{idOrSlug}?format=json -> `{id, slug, title, format, mode, body, links}`.

    Always read with `fmt="json"`: for a single page the route wraps non-JSON-format
    responses in a `<pre>` envelope (live-verified Phase 3). Bearer so unpublished pages
    are readable. `body` never contains the `<page-break>` (stripped on save).
    """
    response = await client.request(
        "GET", _content_path(client, site, id_or_slug), params={"format": fmt}, auth="bearer"
    )
    return unwrap_dict(response)


async def patch_content(
    client: HaxcmsClient,
    site: str,
    id_or_slug: str,
    body: str,
    *,
    schema: list[dict[str, Any]] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """PATCH content/{idOrSlug} -> the updated item record (updateContent → saveNode).

    `body` MUST start with the `<page-break>` envelope — without it saveNode parses zero
    segments and silently writes nothing (still 200). `schema` fills metadata.images/videos;
    `details` merges node details (configure/advanced shapes).
    """
    payload: dict[str, Any] = {"site": {"name": site}, "body": body}
    if schema is not None:
        payload["schema"] = schema
    if details is not None:
        payload["details"] = details
    response = await client.request(
        "PATCH",
        _content_path(client, site, id_or_slug),
        json=payload,
        auth="bearer+site",
        site=site,
    )
    return unwrap_dict(response)


# --- Phase 4: read-only catalogs (API-REF §8) -------------------------------------------------
#
# Bearer-authenticated (optional upstream, consistent with the other reads); the catalog
# service treats every failure here as "live data unavailable" and stays bundled-only.


async def list_blocks(client: HaxcmsClient, site: str) -> dict[str, Any]:
    """GET blocks -> block records + usage counts."""
    response = await client.request("GET", client.site_path(site, "blocks"), auth="bearer")
    return unwrap_dict(response)


async def get_block(
    client: HaxcmsClient, site: str, tag: str, *, include: str | None = None
) -> dict[str, Any]:
    """GET blocks/{tag}[?include=haxProperties,haxSchema,haxElementSchema] -> one record."""
    params = {"include": include} if include else None
    response = await client.request(
        "GET",
        client.site_path(site, f"blocks/{quote(tag, safe='')}"),
        params=params,
        auth="bearer",
    )
    return unwrap_dict(response)


async def list_schemas(
    client: HaxcmsClient, site: str, *, params: dict[str, Any] | None = None
) -> dict[str, Any]:
    """GET schemas?filter.kind=haxProperties&filter.webcomponentName={tag} -> records.

    Served when the instance can find `<pkg>/lib/<tag>.haxProperties.json` in its build.
    """
    response = await client.request(
        "GET", client.site_path(site, "schemas"), params=params, auth="bearer"
    )
    return unwrap_dict(response)


async def get_custom_element(client: HaxcmsClient, site: str, tag: str) -> dict[str, Any]:
    """GET custom-elements/{tag} -> the wc-registry entry (404 when the tag is unknown)."""
    response = await client.request(
        "GET", client.site_path(site, f"custom-elements/{quote(tag, safe='')}"), auth="bearer"
    )
    return unwrap_dict(response)
