"""Files service (PLAN Phase 5 T5.4).

Typed wrappers over the five `client/site_api.py` files helpers: source resolution for
uploads (`resolve_source`), the Phase 5 models for reads, and argument validation for the
PATCH operations.

Live-contract notes:

* All five routes are bearer + site token; mutations ride the upstream file-ops limiter
  (500 per 5 minutes per user:site) — the resulting 429 + Retry-After is mapped to
  RATE_LIMITED by the client envelope layer, so no service-side handling is needed.
* The PATCH `data` response is an open object per site-spec (`additionalProperties: true`)
  and differs per operation, so the operation functions return the raw dict; T5.7 pins the
  live shapes.
* `rename` and `duplicate` are dedicated functions (the PLAN names them separately);
  `delete` uses its own route (site-spec: "Use the DELETE method for the delete operation
  instead"), never PATCH.
"""

from __future__ import annotations

from typing import Any

from haxcms_mcp.client import HaxcmsClient, site_api
from haxcms_mcp.config import Settings
from haxcms_mcp.errors import ErrorCode, HaxcmsMcpError
from haxcms_mcp.models.file import FileCollection, FileRecord, UploadResult
from haxcms_mcp.services.files.sources import resolve_source

# the six PATCH transforms exposed through transform_file
TRANSFORM_OPERATIONS = (
    "convert-jpg",
    "scale",
    "sepia",
    "black-and-white",
    "rotate-90",
    "compress",
)

# compression levels (site-spec: compress `level`, defaults to medium server-side)
COMPRESS_LEVELS = ("light", "medium", "heavy", "maximum")


def _require_uuid(uuid: str) -> str:
    value = (uuid or "").strip()
    if not value:
        raise HaxcmsMcpError(
            ErrorCode.INVALID_ARGUMENT,
            "file uuid must not be empty",
            hint="uuids come from list_files / upload_file (the stable files.json UUID)",
        )
    return value


def _validate_filename(filename: str) -> str:
    """Filename overrides travel as multipart metadata — keep them plain names."""
    name = (filename or "").strip()
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        raise HaxcmsMcpError(
            ErrorCode.INVALID_ARGUMENT,
            f"invalid filename override {filename!r}",
            hint="pass a plain filename with an extension, e.g. Songline_1.png",
        )
    return name


async def list_files(
    client: HaxcmsClient,
    site: str,
    *,
    type: str | None = None,
    extension: str | None = None,
    name_contains: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> FileCollection:
    """GET files -> FileCollection `{count, total, page, files, orphans}`.

    `type` is the server's coarse bucket (image|video|audio|document); `extension` is
    matched without the leading dot (a dot in the argument is stripped); `name_contains`
    filters on the stored name. The route auto-indexes on-disk files missing from
    files.json before returning and flags disk-less records in `orphans`.
    """
    params: dict[str, Any] = {"page.limit": limit, "page.offset": offset}
    if type is not None:
        params["filter.type"] = type
    if extension is not None:
        params["filter.extension"] = extension.lstrip(".").lower()
    if name_contains is not None:
        params["filter.nameContains"] = name_contains
    data = await site_api.list_files(client, site, params=params)
    return FileCollection.from_api(data)


async def upload_file(
    client: HaxcmsClient,
    settings: Settings,
    site: str,
    source: str,
    *,
    filename: str | None = None,
    page: str | None = None,
) -> UploadResult:
    """Resolve `source` (path / URL / data: / base64:) and POST it as multipart.

    `filename` overrides the name the source resolved to. `page` (id or slug) resolves to
    the item id sent as the multipart `nodeId` field, associating the upload with that
    page (T5.7 verifies what the server does with it). The response names the MIME key
    `type` instead of `mimetype` — UploadResult.from_api accepts either.
    """
    resolved = await resolve_source(source, settings)
    name = _validate_filename(filename) if filename is not None else resolved.filename
    node_id: str | None = None
    if page is not None:
        item = await site_api.get_item(client, site, page)
        node_id = str(item.get("id") or "") or None
    data = await site_api.upload_file(
        client,
        site,
        filename=name,
        content=resolved.data,
        mimetype=resolved.mimetype,
        node_id=node_id,
    )
    return UploadResult.from_api(data)


async def get_file(client: HaxcmsClient, site: str, uuid: str) -> FileRecord:
    """GET files/{uuid} -> one FileRecord (404 -> NOT_FOUND via the envelope layer)."""
    data = await site_api.get_file(client, site, _require_uuid(uuid))
    return FileRecord.from_api(data)


async def rename_file(client: HaxcmsClient, site: str, uuid: str, new_name: str) -> dict[str, Any]:
    """PATCH files/{uuid} `{operation: rename, newName}` -> raw operation result.

    Renaming changes the stored name/URL: pages referencing the old `files/<name>` URL
    keep pointing at the old location (HAXcms does not rewrite bodies).
    """
    name = _validate_filename(new_name)
    return await site_api.update_file(client, site, _require_uuid(uuid), "rename", newName=name)


async def transform_file(
    client: HaxcmsClient,
    site: str,
    uuid: str,
    operation: str,
    *,
    size: str | int | None = None,
    level: str | None = None,
) -> dict[str, Any]:
    """PATCH files/{uuid} with one of the six transforms -> raw operation result.

    `size` rides through as a string (site-spec types it string; `scale` consumes it).
    `level` is validated against light|medium|heavy|maximum (compress; the server
    defaults to medium when omitted).
    """
    op = (operation or "").strip().lower()
    if op not in TRANSFORM_OPERATIONS:
        raise HaxcmsMcpError(
            ErrorCode.INVALID_ARGUMENT,
            f"unknown transform {operation!r}",
            hint="operations: " + ", ".join(TRANSFORM_OPERATIONS),
        )
    args: dict[str, Any] = {}
    if size is not None:
        args["size"] = str(size)
    if level is not None:
        value = level.strip().lower()
        if value not in COMPRESS_LEVELS:
            raise HaxcmsMcpError(
                ErrorCode.INVALID_ARGUMENT,
                f"unknown compression level {level!r}",
                hint="levels: " + ", ".join(COMPRESS_LEVELS),
            )
        args["level"] = value
    return await site_api.update_file(client, site, _require_uuid(uuid), op, **args)


async def duplicate_file(client: HaxcmsClient, site: str, uuid: str) -> dict[str, Any]:
    """PATCH files/{uuid} `{operation: duplicate}` -> raw result (a NEW uuid is minted)."""
    return await site_api.update_file(client, site, _require_uuid(uuid), "duplicate")


async def delete_file(client: HaxcmsClient, site: str, uuid: str) -> dict[str, Any]:
    """DELETE files/{uuid} -> raw deletion result (the disk file and files.json entry go).

    Bodies referencing `files/<name>` are NOT rewritten — dangling media-image sources
    stay in the HTML.
    """
    return await site_api.delete_file(client, site, _require_uuid(uuid))
