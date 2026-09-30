"""Shared pytest fixtures (PLAN.md Section 6.2).

Phase 0 provides: `haxcms` (session-scoped live instance), `settings` (per test, pointing at the
runtime with credentials), `mcp` (FastMCP app + in-memory client). Phase 1 adds `client` (a
logged-in HaxcmsClient). The `site` and `page` fixtures arrive with Phases 2-3.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from fastmcp import Client

from haxcms_mcp.client import HaxcmsClient
from haxcms_mcp.config import Settings
from haxcms_mcp.server import build_server
from tests.harness.haxcms_runtime import HaxcmsRuntime
from tests.harness.mcp_client import McpTestClient

# NOTE: the --snapshot-update flag comes from the syrupy pytest plugin (installed);
# tests/harness/snapshots.py reuses it for the plain-JSON snapshots.


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip `network`-marked tests unless HAXCMS_MCP_TEST_NETWORK=1 (PLAN §6.1)."""
    if os.environ.get("HAXCMS_MCP_TEST_NETWORK", "").lower() in {"1", "true", "yes"}:
        return
    skip_network = pytest.mark.skip(reason="needs HAXCMS_MCP_TEST_NETWORK=1")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip_network)


@pytest.fixture(scope="session")
async def haxcms() -> AsyncIterator[HaxcmsRuntime]:
    """One real HAXcms NodeJS instance for the whole test session."""
    async with HaxcmsRuntime() as runtime:
        yield runtime


@pytest.fixture
def settings(haxcms: HaxcmsRuntime) -> Settings:
    """Per-test Settings pointing at the live runtime with its credentials."""
    return Settings(
        base_url=haxcms.base_url,
        username=haxcms.username,
        password=haxcms.password,
    )


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[HaxcmsClient]:
    """A HaxcmsClient pointed at the live runtime, logged in (PLAN §6.2)."""
    async with HaxcmsClient(settings) as haxcms_client:
        await haxcms_client.auth.ensure_access()
        yield haxcms_client


@pytest.fixture
async def mcp(settings: Settings) -> AsyncIterator[McpTestClient]:
    """Fresh FastMCP app plus in-memory client for one test."""
    server = build_server(settings)
    async with Client(server) as client:
        yield McpTestClient(server, client)
