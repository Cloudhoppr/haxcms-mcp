# PROGRESS.md: Handoff log

This file is the only memory that survives between Sessions. The implementing agent appends one
section per Phase when the Phase's exit checklist (PLAN.md §0.5) is complete. Never delete earlier
sections. `PLAN.md` is read-only; deviations are recorded here.

Read order at the start of a Session: PLAN.md §0 → CONTEXT.md → this file → the Phase section.

## Status board

| Phase | Title | Status | Tag | Commit |
|---|---|---|---|---|
| 0 | Scaffold and CI | done | `phase-00` | see tag |
| 1 | Core client and session tools | done | `phase-01` | see tag |
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
- (Phase 1, live probe) `GET /system/api/v1/session` with bearer → 200 with TOP-LEVEL
  `{status, authenticated, jwt, user}` — no `data` key; anonymous → 401 with top-level `message`.
  `unwrap()` therefore falls back to the whole body when `data` is absent.
- (Phase 1, spec + live) `session/user`, `status`, `system/version` all require bearer AND
  `X-HAXCMS-User-Token` per their `security:` blocks in `specs/system-spec.yaml`; anonymous → 401
  "Authentication required". `GET system/version` → `data: {"version": "26.8.0"}` — the instance
  self-reports 26.8.0 although it is installed from npm `@haxtheweb/haxcms-nodejs@26.8.1`;
  `status` reports `haxcmsVersionCurrent: "26.8.0"` and a newer `haxcmsVersionLatest`.
- (Phase 1, live probe) `GET session/refresh` returns an IDENTICAL jwt when called within the same
  second as the previous issuance — tests must assert on refresh-call counts / route hits, never on
  token inequality.
- (Phase 1, live probe) `POST session/logout` → `{status: 200, data: "loggedout"}`.
- (Phase 1, live test, T1.4 verification) `siteToken` differs per site: two created sites got
  different tokens via connection-settings + per-site Referer; a `POST items` write to site B
  carrying site A's token → 403. The same write with the correct bearer+site token → 200.
- (Phase 1, live test) Login rate limiter: repeated wrong-password logins for a THROWAWAY username
  hit 429 "Too many failed login attempts" within ≤7 attempts; the envelope mapper surfaces it as
  RATE_LIMITED with "(retry after Xs)". Use a throwaway user in tests — the limiter is per
  IP+username and would otherwise lock out the real test user for 15 minutes.
- (Phase 1, live test) Raw create-site per API-REF §3.3 (theme `clean-one`, build type `skeleton` /
  `from-skeleton`, one inline home item) works with bearer+user; raw createNode
  `POST /_sites/{site}/x/api/v1/items` accepts the single-form payload
  `{site:{name}, node:{id:null,title,location:null,duplicate:null,contents}, parent:null,
  order:null, indent:null, description:"", metadata:null}` with bearer+site token.

## Environment notes

- HAXcms install time / boot time on this machine: npm install of
  `@haxtheweb/haxcms-nodejs@26.8.1` ≈ 35s (warm npm cache) into `.haxcms-runtime/`; first boot of
  a session ≈ 35s (cold node + boilerplate copy), subsequent boots ≈ 1.7s; full integration suite
  (4 tests, two boots) ≈ 38s cached / ~77s including the first install.
- Phase 1 timings: live `integration or functional` (14 tests, incl. two site
  create/archive cycles) ≈ 13s warm; full `uv run pytest -m "not e2e"` (92 tests) ≈ 17s.
- Node version used: v22.23.3 (npm 10.9.9); system Python 3.13.6, project pinned 3.12
  (`.python-version`), uv 0.8.4.
- fastmcp version pinned: `==4.0.10` (pyproject), mcp SDK v2 types via `fastmcp.mcp_types`.
- Windows/PowerShell: multi-line commit messages go through `.git/COMMIT_MSG_TMP` + `git commit -F`
  because PowerShell 5.1 mangles embedded double quotes in native-exe args. Keep `"` out of commit
  messages. Write the message file with the editor/Write tooling, NOT `Set-Content -Encoding utf8`
  (PS 5.1 adds a BOM that ends up inside the commit subject; amend with `git commit --amend -F` if
  it happens).
- Bash tool is rejected by the user in this workspace; use PowerShell for all shell work.
- pytest-asyncio: with `asyncio_default_fixture_loop_scope = "session"`, async TESTS must also run
  on the session loop (`asyncio_default_test_loop_scope = "session"` in pyproject). A
  function-loop test awaiting a session-loop-bound fixture (the fastmcp in-memory `Client` task
  group in the `mcp` fixture) deadlocks with ZERO cpu usage and no error — diagnosed with
  `uvx py-spy dump --pid <pytest pid>`. py-spy is not a project dependency; use `uvx` on demand.
- httpx gotcha: `client.build_request(..., timeout=None)` DISABLES the timeout (the client-level
  default only applies when the argument is omitted). `HaxcmsClient.request` must only forward
  `timeout` when it is not None.
- A killed integration run orphans the harness node process and its `%TEMP%\haxcms-mcp-rt-*` /
  `haxcms-mcp-home-*` dirs; clean them up manually (taskkill /F /T /PID + remove the specific
  dirs). The auto-mode classifier denies wildcard TEMP sweeps — name the resolved paths.

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

---

### Phase 1: Core client and session tools

**Session:** shared with Phase 0 (compacted several times)
**Completed:** 2026-09-30, tag `phase-01`, final commit: see tag

**Built**
- `src/haxcms_mcp/client/budget.py` — `OutboundBudget` token bucket (rate/capacity/max_wait from
  settings, injectable clock+sleep, negative-reservation queueing, `BudgetStats`
  tokens/waits/denials); denial → RATE_LIMITED with `details.retry_after_s` and a hint naming the
  `HAXCMS_MCP_RATE_*` env vars.
- `src/haxcms_mcp/client/retry.py` — `RetryPolicy` + `with_retry`: 429 sleeps Retry-After
  (cap 60s, default 2s) up to retry_max; 502/503/504 + connection errors retry GET/HEAD only on
  0.5/1/2s backoff; POST/PATCH/DELETE never retried on transient; TimeoutException → TIMEOUT,
  other TransportError → UPSTREAM_ERROR; `on_retry` hook re-charges the budget between attempts.
- `src/haxcms_mcp/client/envelope.py` — `response_message`, `is_invalid_bearer`,
  `error_from_response` (exact upstream messages kept verbatim, full mapping table per PLAN §2.3,
  429 appends "(retry after Xs)"), `unwrap` (falls back to the whole body when there is no `data`
  key — GET /session is shaped that way) and `unwrap_full` (keeps jwt/link/id/slug extras).
- `src/haxcms_mcp/client/auth.py` — `parse_app_settings` + `AuthManager`: login stores jwt and
  `haxcms_refresh_token` cookie; proactive refresh at 12 of 15 minutes; reactive refresh once on
  403 "Invalid bearer token"; refresh never sends Origin/Referer and rotates the cookie; explicit
  logout sets a `_logged_out` flag suppressing auto-login until an explicit login; userToken
  cached once, siteTokens per site via connection-settings + Referer `{base}/_sites/{site}/`.
- `src/haxcms_mcp/client/__init__.py` — `HaxcmsClient`: one `httpx.AsyncClient(base_url,
  timeout)` + AuthManager + budget + policy; `request(method, path, auth=none|bearer|bearer+user|
  bearer+site, site, timeout, accept, headers, no_retry)`; `sys()` / `site_path()` builders;
  `get_json/post_json/patch_json/delete_json` (unwrapped), `*_full` variants, `download()` bytes.
- `src/haxcms_mcp/client/system_api.py` — typed helpers: login/refresh/logout (auth=none,
  no_retry), session (bearer), session_user/status/version/list_sites (bearer+user).
- `src/haxcms_mcp/models/common.py` (`Envelope`, `PageInfo`), `models/site.py` (`SiteListEntry`,
  `SiteList` with `from_api` mapping the `metadata.site` shape).
- `src/haxcms_mcp/tools/_common.py` (`tool_annotations`, `resolve_site`), `tools/auth.py` —
  the four Session Tools; `server.py` registers them. `get_server_info` probes live version and
  status best-effort (`version_error`/`status_error` instead of failing).

**Tests added**
- unit: `test_p01_budget.py` (8), `test_p01_retry.py` (11), `test_p01_envelope.py` (16),
  `test_p01_auth.py` (13, respx + captured fixture), `test_p01_client.py` (10) — 58 new;
  `test_p00_server_boot.py` updated for the four-tool registry.
- integration: `test_p01_live_auth.py` (7) — lifecycle incl. forced refresh and logout,
  session/status/version/list endpoints, whoami tool, live get_server_info, wrong password,
  rate limiter (throwaway username), per-site tokens + wrong-site 403 (creates/archives two sites
  with raw calls per API-REF §3.3).
- regression: `test_p01_snapshots.py` + `auth_header_matrix.json` (headers per auth mode);
  `tool_schemas.json` regenerated for four tools.
- functional: `test_p01_login_journey.py` (3) — login journey, env-credentials whoami, read-only
  mode blocks login but allows whoami.
- fixtures: `tests/fixtures/connection_settings.js` captured from the live 26.8.1 instance.
- full rerun: `uv run pytest -m "not e2e"` → green (92 tests; see tag).

**Verified facts** — see the cumulative list (all Phase 1 bullets), including the T1.4
site-token verification (differs per site; wrong-site token → 403).

**Deviations from PLAN.md**
- login/refresh/logout use `no_retry=True`: PLAN's retry policy would sleep the Retry-After of a
  429 (up to 15 min on the login limiter) inside an interactive tool call; surfacing RATE_LIMITED
  immediately with the retry-after in the message is the usable behaviour. Data calls keep the
  full policy.
- `whoami` after explicit `logout` fails AUTH_REQUIRED even with env credentials (the
  `_logged_out` flag) — required to satisfy both PLAN Phase 1 stories (integration: logout →
  whoami fails; functional: env credentials → whoami works without login).
- `get_server_info` payload grew `haxcms` (version/status probe) and `no_auth` keys vs the Phase 0
  stub; tool-schema snapshot updated deliberately.
- One extra fix commit beyond PLAN's list: `fix(core): enforce client timeout and align event
  loop scopes` — `build_request(timeout=None)` disabled all httpx timeouts, and pytest-asyncio
  needed `asyncio_default_test_loop_scope = "session"` (function-loop tests deadlocked silently
  against the session-loop `mcp` fixture; diagnosed with `uvx py-spy dump`).
- Commit ordering follows PLAN exactly; note the auth-commit unit tests import `HaxcmsClient`, so
  the tree is only fully green from the pipeline commit onward (PLAN's own order entangles them).

**Known gaps / follow-ups**
- The live suite creates and archives two sites per run (test_site_tokens...); if a run is killed
  mid-test, orphan node processes/temp dirs remain (see Environment notes).
- `resolve_site` exists but is unused until Phase 2 tools arrive.

**Notes for the next Session**
- Phase 2 imports: `HaxcmsClient.request/get_json/post_json/...`, `system_api`, `models`,
  `tools/_common.py` helpers, and the conftest `client`/`mcp` fixtures — all ready.
- Check each site route's `security:` block in `specs/site-spec.yaml` before choosing the auth
  mode (API-REF §2.6 was already wrong once for listSites).
- The permission classifier ("qwen ... temporarily unavailable") still times out intermittently;
  retry after a minute or do Write/Edit work meanwhile.
