"""Phase 4 regression snapshots (PLAN §6.4, Phase 4 regression list).

* `page_break`: the envelope contract with saveNode.js/pageBreakParser — attribute order,
  canonical flag values, escaping, and absence-means-false/deletes reproduction.

Later Phase 4 commits extend this file with the serializer and catalog snapshots.
Update deliberately with `pytest --snapshot-update`.
"""

from __future__ import annotations

from typing import Any

import pytest

from haxcms_mcp.models.item import Item
from haxcms_mcp.services.content.page_break import build_page_break
from tests.harness.snapshots import assert_or_update_snapshot

pytestmark = pytest.mark.regression

FULL_RECORD: dict[str, Any] = {
    "id": "item-123",
    "title": 'A "Quoted" <Title> & More',
    "slug": "unit-1/song-lines",
    "parent": "item-unit-1",
    "indent": 2,
    "order": 7,
    "description": "A description with & ampersand",
    "metadata": {
        "published": True,
        "locked": True,
        "hideInMenu": True,
        "pageType": "lesson",
        "tags": ["week-1", "intro"],
        "relatedItems": ["item-2", "item-3"],
        "image": "files/cover.png",
        "icon": "hax:lesson",
        "accentColor": "purple",
        "theme": {"element": "clean-one", "path": "@haxtheweb/clean-one", "key": "clean-one"},
        "overridePathauto": True,
        "linkUrl": "https://example.com/x",
        "linkTarget": "_blank",
    },
}

MINIMAL_RECORD: dict[str, Any] = {
    "id": "item-1",
    "title": "Home",
    "slug": "home",
    "metadata": {},
}

UNPUBLISHED_RECORD: dict[str, Any] = {
    "id": "item-9",
    "title": "Draft",
    "slug": "draft",
    "metadata": {"published": False},
}


def _page_break_goldens() -> dict[str, str]:
    return {
        "full": build_page_break(Item.from_api(FULL_RECORD)),
        "minimal": build_page_break(Item.from_api(MINIMAL_RECORD)),
        "unpublished": build_page_break(Item.from_api(UNPUBLISHED_RECORD)),
    }


def test_page_break_goldens(request: pytest.FixtureRequest) -> None:
    update = bool(request.config.getoption("--snapshot-update", default=False))
    assert_or_update_snapshot("page_break", _page_break_goldens(), update=update)
