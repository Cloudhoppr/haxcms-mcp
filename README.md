# haxcms-mcp

An MCP (Model Context Protocol) server that lets an AI agent operate a self-hosted
[HAXcms NodeJS](https://github.com/haxtheweb/haxcms-nodejs) instance the way a human author does
through the HAX dashboard and editor: create and manage sites, build outlines, author page content
with the full block catalog, upload files, change themes, import documents, and export artifacts.

> **Status: under construction.** Phase 0 (scaffold, CI, test harness) is complete. Tools arrive
> phase by phase per [`PLAN.md`](./PLAN.md); progress is tracked in
> [`PROGRESS.md`](./PROGRESS.md).

## Install

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone <this repo> && cd haxcms-mcp
uv sync
```

## Run

Point the server at a running HAXcms NodeJS instance via environment variables (prefix
`HAXCMS_MCP_`, see PLAN.md Section 4 for the full table):

```bash
export HAXCMS_MCP_BASE_URL=http://localhost:3000
export HAXCMS_MCP_USERNAME=admin
export HAXCMS_MCP_PASSWORD=secret

uv run haxcms-mcp                    # stdio transport (default)
uv run haxcms-mcp --transport http --host 127.0.0.1 --port 8765 --path /mcp
```

## Development

```bash
uv run pytest -m unit                            # fast, no Node required
uv run pytest -m "integration or functional"     # spawns a real HAXcms (Node 18.20.3+/npm)
uv run pytest -m regression                      # snapshots + golden outputs
uv run ruff check . && uv run mypy src           # lint + types
```
