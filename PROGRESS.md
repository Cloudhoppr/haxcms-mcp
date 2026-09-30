# PROGRESS.md: Handoff log

This file is the only memory that survives between Sessions. The implementing agent appends one
section per Phase when the Phase's exit checklist (PLAN.md §0.5) is complete. Never delete earlier
sections. `PLAN.md` is read-only; deviations are recorded here.

Read order at the start of a Session: PLAN.md §0 → CONTEXT.md → this file → the Phase section.

## Status board

| Phase | Title | Status | Tag | Commit |
|---|---|---|---|---|
| 0 | Scaffold and CI | done | `phase-00` | see tag |
| 1 | Core client and session tools | not started | | |
| 2 | Site lifecycle tools | not started | | |
| 3 | Outline and page tools | not started | | |
| 4 | Content and block tools | not started | | |
| 5 | Files | not started | | |
| 6 | Site settings | not started | | |
| 7 | Imports and generated converters | not started | | |
| 8 | Exports | not started | | |
| 9 | Prompts, docs, hardening, e2e | not started | | |

## Verified facts (cumulative)

Facts that PLAN.md or docs/haxcms-api-reference.md asked to "verify". One bullet each, with the
Phase that verified it and how (file:line in haxcms-nodejs, or a live-instance observation).

- (Phase 0, live) HAXcms 26.8.1 boots from the API-REF §11 recipe on Windows: `HAXCMS_ROOT` with
  trailing slash + `PORT` + `HOME`/`USERPROFILE` + git identity env vars, `node dist/app.js` from
  the npm package; ready = any HTTP status from `GET /system/api/v1/status`.
  `tests/harness/haxcms_runtime.py` implements it; proven by `tests/integration/test_p00_harness.py`.
- (Phase 0, live) `POST /system/api/v1/session/login` returns `{status:200, jwt}` (jwt has 2 dots)
  and sets the `haxcms_refresh_token` cookie; wrong password → 401.
- (Phase 0, live + spec) **`GET /system/api/v1/sites` requires bearer AND `X-HAXCMS-User-Token`.**
  Bearer-only returns 403 `{"status":403,"data":{"message":"X-HAXCMS-User-Token header is required
  for this endpoint"}}`. The 26.8.1 spec (`specs/system-spec.yaml` L322-330, `listSites`) declares
  `security: [bearerAuth, userTokenHeader]`; API-REF §2.6's "System admin reads ... user token: no"
  row is OUTDATED for list sites. The server builds its route→policy map from the bundled OpenAPI
  spec and fails closed to `authenticated` (`haxcms-nodejs src/app.js` L2034-2077,
  `readSystemApiAuthPoliciesFromOpenApiSpec` / `enforceSystemApiUserTokenPolicy`). **Phase 1+:
  treat `specs/*.yaml` security blocks, not API-REF §2.6, as the source of truth for headers.**
- (Phase 0, live) `GET /system/api/v1/session/connection-settings` with `Accept:
  application/javascript` and NO Referer returns `window.appSettings = {...}` including a valid
  `userToken` on a fresh instance with zero sites (`userToken = getRequestToken(activeUser)` is
  site-independent, `connectionSettings.js` L208). Parse: index of `window.appSettings`, then
  `json.JSONDecoder().raw_decode` from the first `{`.
- (Phase 0, live) Fresh instance: `GET /system/api/v1/sites` (bearer + user token) → `{status:200,
  data:{items: []}}`.
- (Phase 0, probes + unit tests) fastmcp 4.0.10: exceptions other than `ToolError` raised in tool
  bodies are masked BELOW the middleware chain into `ToolError("Error calling tool '<name>':
  <original str>")` with the original as `__cause__`; the error-translation middleware must unwrap
  `__cause__` (`src/haxcms_mcp/middleware/errors.py`). No `mcp.get_tools()`; use `await
  mcp.list_tools()` / `await mcp.get_tool(name)`. Details in `docs/fastmcp-notes.md`.

## Environment notes

- HAXcms install time / boot time on this machine: npm install of
  `@haxtheweb/haxcms-nodejs@26.8.1` ≈ 35s (warm npm cache) into `.haxcms-runtime/`; first boot of
  a session ≈ 35s (cold node + boilerplate copy), subsequent boots ≈ 1.7s; full integration suite
  (4 tests, two boots) ≈ 38s cached / ~77s including the first install.
- Node version used: v22.23.3 (npm 10.9.9); system Python 3.13.6, project pinned 3.12
  (`.python-version`), uv 0.8.4.
- fastmcp version pinned: `==4.0.10` (pyproject), mcp SDK v2 types via `fastmcp.mcp_types`.
- Windows/PowerShell: multi-line commit messages go through `.git/COMMIT_MSG_TMP` + `git commit -F`
  because PowerShell 5.1 mangles embedded double quotes in native-exe args. Keep `"` out of commit
  messages. Write the message file with the editor/Write tooling, NOT `Set-Content -Encoding utf8`
  (PS 5.1 adds a BOM that ends up inside the commit subject; amend with `git commit --amend -F` if
  it happens).
- Bash tool is rejected by the user in this workspace; use PowerShell for all shell work.

---

## Phase template (copy for each Phase)

### Phase N: <title>

**Session:** fresh | shared with Phase M (compacted between)
**Completed:** YYYY-MM-DD, tag `phase-NN`, final commit `<sha>`

**Built**
- bullet per module or tool group, with paths

**Tests added**
- unit: files and count
- integration: files and count
- regression: snapshot files touched
- functional: files and count
- full regression rerun command and result

**Verified facts** (also copied into the cumulative list above)
- ...

**Deviations from PLAN.md**
- what, why, and what the next Phase must know

**Known gaps / follow-ups**
- ...

**Notes for the next Session**
- anything that saved time or cost time

---

### Phase 0: Scaffold and CI

**Session:** fresh (continued in-session after two context compactions; subagent-per-Phase protocol
replaced by sequential in-session execution — see Deviations)
**Completed:** 2026-09-30, tag `phase-00`, final commit: see tag

**Built**
- `pyproject.toml`: uv package, Python 3.12, `fastmcp==4.0.10`, httpx, pydantic v2,
  pydantic-settings, lxml, pyyaml, anyio; dev: pytest(+asyncio auto mode, +cov), respx, syrupy,
  ruff (line-length 100; E,F,W,I,UP,B,SIM), mypy strict + pydantic plugin; script
  `haxcms-mcp = haxcms_mcp.__main__:main`; markers unit/integration/functional/regression/e2e/
  needs_chrome/slow/network.
- `src/haxcms_mcp/config.py` — `Settings` (env prefix `HAXCMS_MCP_`, `.env`, extra=ignore), all
  PLAN §4 vars; BASE_URL normalisation (strip, require http(s)://, strip trailing /);
  `input_roots: Annotated[list[Path], NoDecode]` split on `os.pathsep` (default `[cwd]`).
- `src/haxcms_mcp/errors.py` — `ErrorCode(StrEnum)` (13 codes), `HaxcmsMcpError` with
  `.formatted` → `[CODE] message. hint`.
- `src/haxcms_mcp/logging.py` — stderr-only logging (stdio-safe; `Context.info()` is deprecated in
  fastmcp 4, SEP-2577), idempotent `configure_logging`, `get_logger`.
- `src/haxcms_mcp/server.py` — `build_server(settings)`; middleware order ReadOnly → ToolLogging →
  ErrorTranslation (first added = outermost); one tool `get_server_info` (read-only annotated).
- `src/haxcms_mcp/__main__.py` — argparse CLI (`--transport stdio|http`, `--host/--port/--path`,
  `--log-level`, `--version`); config errors → stderr + exit 2.
- `src/haxcms_mcp/middleware/{read_only,logging,errors}.py` — see verified facts for the
  `__cause__`-unwrapping requirement in errors.py. Logging middleware logs argument KEYS only
  (never values — credentials).
- `docs/fastmcp-notes.md` — 11 sections of empirically probed fastmcp 4.0.10 APIs.
- `scripts/sync_specs.py` (`--from <checkout>` | `--tag <ref>`) + vendored `specs/`:
  system-spec.yaml, site-spec.yaml from haxcms-nodejs 26.8.1 @ e969655c; `specs/VERSION`.
- `tests/harness/haxcms_runtime.py` — installs the npm package into `.haxcms-runtime/` (or uses
  `HAXCMS_MCP_TEST_HAXCMS_DIR`), boots an isolated instance per API-REF §11, records
  install/boot seconds, teardown via `taskkill /F /T` (win) / `killpg` (posix) + rmtree unless
  `HAXCMS_MCP_TEST_KEEP_RUNTIME`. Helpers: `site_dir`, `read_site_json`, `read_page_html`.
- `tests/harness/mcp_client.py` — `McpTestClient` (call/call_error/list_tool_names/read_resource)
  over the fastmcp in-memory `Client`.
- `tests/harness/snapshots.py` — canonical-JSON snapshots under
  `tests/regression/snapshots/*.json`; created on first run, updated with syrupy's
  `--snapshot-update` flag; mismatch → unified diff AssertionError.
- `tests/conftest.py` — fixtures `haxcms` (session), `settings`, `mcp`; `network`-marker skip
  unless `HAXCMS_MCP_TEST_NETWORK=1`.
- `.github/workflows/ci.yml` — `lint-unit` (ubuntu, py3.12+3.13: ruff, ruff format, mypy, unit +
  coverage), `integration` (node 22, `.haxcms-runtime` cache keyed on specs/VERSION +
  pyproject.toml, `pytest -m "not e2e and not unit"`), `e2e` (PRs to main only).
- `README.md` stub; directory placeholders for all PLAN §3 modules.

**Tests added**
- unit: `test_p00_settings.py`, `test_p00_errors.py`, `test_p00_server_boot.py` — 19 tests.
- integration: `test_p00_harness.py` — 4 tests (boot+disk layout, status, login/list-sites incl.
  user-token fact, teardown removes runtime dir).
- regression: `test_p00_snapshots.py` + `tests/regression/snapshots/tool_schemas.json`
  (`get_server_info` only).
- functional: none (PLAN: no user-facing feature yet).
- full rerun: `uv run pytest -m "not e2e"` → all green (see commit).

**Verified facts** — see cumulative list above (all Phase 0 bullets).

**Deviations from PLAN.md**
- §0.3 one-subagent-per-Phase protocol NOT followed: Agent spawning was denied by the permission
  system. All Phases run sequentially in this Session; this file remains the handoff record and
  gets a full entry per Phase regardless.
- Bash tool rejected by user → PowerShell for everything. Commit messages avoid `"` and go via
  `git commit -F .git/COMMIT_MSG_TMP`.
- `client`/`site`/`page` conftest fixtures deferred to Phases 1-3 (they wrap modules that do not
  exist yet); Phase 0 ships `haxcms`/`settings`/`mcp` only.
- Regression snapshots are plain JSON (PLAN §6.4 names one file,
  `tests/regression/snapshots/tool_schemas.json`), not syrupy `.ambr`; syrupy's `--snapshot-update`
  flag is reused (defining our own addoption collides with the plugin).
- `ErrorCode` is a `StrEnum` (ruff UP042), not `(str, Enum)`.

**Known gaps / follow-ups**
- API-REF §2.6 header matrix is wrong for `listSites` (needs user token). Later Phases must check
  each route's `security:` block in `specs/system-spec.yaml` / `specs/site-spec.yaml` before coding
  the header matrix into `HaxcmsClient.request(auth=...)`.
- e2e workflow exists but the e2e suite is empty until Phase 9.
- `.haxcms-runtime/` npm cache is gitignored; first CI/local run pays the install cost.

**Notes for the next Session**
- Run integration with `uv run pytest -m integration -q -s` to see `[harness]` install/boot timings
  on stderr.
- The permission classifier intermittently times out ("qwen ... temporarily unavailable"); retry
  the same command after a minute, or do Write/Edit work meanwhile.
- fastmcp masking gotcha (see verified facts) will bite any middleware work in Phase 1 — read
  `docs/fastmcp-notes.md` §3 first.
