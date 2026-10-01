"""Content models (PLAN Phase 4).

`Block` is the §2.3 block record the parser produces and the anchor resolver searches.
Phase 4's content service adds `PageContent` and `BlockOpResult` here (T4.3).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Block(BaseModel):
    """One top-level content block: `{index, tag, attributes, text, html, preview}`.

    `text` is the whitespace-collapsed text of the whole subtree; `html` is the block's
    serialized outer HTML; `preview` is the first 80 characters of `text`, falling back to
    `html` for text-less blocks (media) so anchor errors stay informative.
    """

    model_config = ConfigDict(extra="allow")

    index: int
    tag: str
    attributes: dict[str, str] = {}
    text: str = ""
    html: str = ""
    preview: str = ""
