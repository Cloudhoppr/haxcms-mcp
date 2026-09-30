"""Site models (PLAN Phase 1 T1.8; full set arrives in Phase 2 T2.1)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class SiteListEntry(BaseModel):
    """One entry of `GET /system/api/v1/sites` `data.items`.

    Each item is a site.json without `items`, plus `location`, `slug`, and `metadata.pageCount`;
    the Site Name lives at `metadata.site.name` (API-REF §3.1).
    """

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    name: str
    title: str = ""
    description: str = ""
    slug: str | None = None
    location: str | None = None
    page_count: int | None = None

    @classmethod
    def from_api(cls, item: dict[str, Any]) -> SiteListEntry:
        metadata = item.get("metadata") or {}
        site_meta = metadata.get("site") or {}
        handled = {"title", "description", "slug", "location", "metadata", "items"}
        extras = {key: value for key, value in item.items() if key not in handled}
        return cls(
            name=str(site_meta.get("name") or item.get("name") or ""),
            title=str(item.get("title") or ""),
            description=str(item.get("description") or ""),
            slug=item.get("slug"),
            location=item.get("location"),
            page_count=metadata.get("pageCount"),
            **extras,
        )


class SiteList(BaseModel):
    """`data` of `GET /system/api/v1/sites`: `{id, title, items}`."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    title: str = ""
    items: list[SiteListEntry] = []

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> SiteList:
        items = [SiteListEntry.from_api(item) for item in data.get("items") or []]
        extras = {key: value for key, value in data.items() if key not in {"id", "title", "items"}}
        return cls(id=data.get("id"), title=str(data.get("title") or ""), items=items, **extras)
