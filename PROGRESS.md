# PROGRESS.md: Handoff log

This file is the only memory that survives between Sessions. The implementing agent appends one
section per Phase when the Phase's exit checklist (PLAN.md §0.5) is complete. Never delete earlier
sections. `PLAN.md` is read-only; deviations are recorded here.

Read order at the start of a Session: PLAN.md §0 → CONTEXT.md → this file → the Phase section.

## Status board

| Phase | Title | Status | Tag | Commit |
|---|---|---|---|---|
| 0 | Scaffold and CI | not started | | |
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

- (none yet)

## Environment notes

- HAXcms install time / boot time on this machine: (Phase 0 fills in)
- Node version used: 
- fastmcp version pinned: 

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
