# Handoff

## Verified State

- Branch: `main`. HEAD before this post-handoff documentation work was `f6aeca7`
  (`Harden production cells and contain OpenCode temp files`); use `git log -1`
  for the new handoff commit created by the procedure.
- Jimbo restarted successfully as PID `211363` at 2026-07-29 14:17 local time
  with the `openai/gpt-5.4-mini` profile, but a post-handoff audit at 14:51 found
  that PID gone and no replacement Jimbo process. `jimbo.log` ends at 14:48:50
  without a traceback. The cause has not been diagnosed; do not describe Jimbo
  as running or restart it without current verification and user direction.
- Production-cell Steps 1 and 2 are committed but still unreachable from player
  chat: the classifier, dispatch, and reply integration in Step 3 are not wired.
- `AGENTS.md` is authoritative. Read `OPERATIONS.md` for runtime/provider
  procedures, `PROD_CELL_PLACE.md` for the production-cell contract, and
  `FUTURE_DIRECTIONS.md` before feature work based on live findings.

## Completed Work

### Production-cell Steps 1 and 2

The initial implementation was re-reviewed against Factorio 2.1.12 and corrected:

- Strict GPS parsing now requires an explicit candidate and requesting player,
  rejects nonfinite or mismatched-surface coordinates, and floors to an integer
  bottom-left tile anchor.
- Phase 1 rejects locked recipes, invalid surface conditions, fluid ingredients
  or products, and unheated Aquilo cells. It resolves compatible placeable
  machines from every `LuaRecipePrototype.categories` entry with the live
  `crafting-category` prototype filter; it no longer uses the nonexistent
  singular `category` or treats the product entity as the crafting machine.
- Half-tile entity centers and west-facing inserters now match live entity
  geometry. Both phases scan the full bounding box and check every component
  with `script_ghost`, requester logistic coverage, full-cell construction
  coverage, planned-pole supply, and mutual wire reach to live power.
- Phase 2 revalidates prototypes and dimensions immediately before mutation,
  creates the six ghosts in one `pcall`, verifies the assigned recipe, copies
  recipe settings through the requesting player, checks every ingredient filter
  and construction registration, and rolls back in reverse order with survivor
  reporting. Mutation remains `retry=False`.
- `PROD_CELL_PLACE.md`, `FUTURE_DIRECTIONS.md`, and `OPERATIONS.md` now describe
  the implemented limits and live Factorio 2.1 findings accurately.

Live validation was read-only: Phase 1 selected
`ANCHOR:-622,51,4,4,electromagnetic-plant` for electronic circuits on Nauvis;
the generated Phase 2 parsed successfully in an unreachable branch; its complete
preflight executed successfully when truncated immediately before
`create_entity`; and processing units returned the expected unsupported-fluid
error. No production-cell ghosts or entities were created.

### OpenCode temporary-file containment

- OpenCode 1.18.9 was identified as the source of roughly 1,410 leaked hidden
  FFF `libfff_c` copies that had consumed about 7.9 GB in `/tmp`.
- `ask_opencode()` now gives every invocation a private
  `tempfile.TemporaryDirectory` through `TMPDIR`; cleanup occurs after success or
  failure. The historical artifacts were fingerprinted and permanently deleted.
- Jimbo was restarted with the fix. Subsequent real model activity completed
  with no leaked top-level `.so`/`.node` file and no abandoned private TMPDIR.
- `OPERATIONS.md` records the diagnosis, direct-OpenAI alternative, and the
  verified `nohup setsid` launch requirement. A plain `nohup` launch from the
  development runner was reaped when its launcher exited.

### Announcement history

- `STARTUP_ANNOUNCEMENTS.md` is a tracked developer/operator history containing
  30 recovered player-visible update announcements: all 28 handcrafted summaries
  in the available server log plus two earlier model-generated announcements.
- `AGENTS.md` now requires the exact new `startup_change_summary` text to be
  appended to that history in the same edit. Generic restarts are excluded.

### Post-handoff landfill dotboard experiment

- Morgan3rd requested a repeating sparse landfill board for Spidertron travel.
  A direct Codex RCON experiment delivered and verified a tile-only blueprint
  with 16 single landfill dots on a five-tile square lattice in a 20 x 20
  relative snap cell. Morgan reported that it looked repeatable; actual
  Spidertron traversal remains untested.
- `FUTURE_DIRECTIONS.md` records the feature request, reference and prototype
  geometry, safe creation and rollback requirements, and opaque chat-link
  behavior. `OPERATIONS.md` records that remote-view players can require access
  through their physical character inventory.

## Validation

Prior code validation for `f6aeca7`:

- `python -m py_compile jimbo.py test_jimbo.py`
- `python -m unittest test_jimbo` — 67 deterministic tests pass.
- Live Factorio version: `2.1.12`.
- Runtime containment verified after real post-restart model calls; `/tmp` had no
  matching leaked artifacts or abandoned `jimbo-opencode-*` directories.

Current documentation-only handoff:

- `git diff --check`
- No Python code changed, so the code test suite was not rerun.

## Remaining Work

### Production-cell integration and deferred extensions

| Step | Description | Status |
|---|---|---|
| 1 | Explicit GPS preflight and machine resolution | complete |
| 2 | Ghost placement, verification, rollback | complete |
| 3 | Classifier prompt, decision branch, dispatch, reply hint | next, awaiting user confirmation |
| 4 | Extension-pole chain or shifted layout | deferred |
| 5 | Automatic/player-relative location search without GPS | deferred |
| 6 | Optional prototype caching and selection refinement | deferred |

The standalone `parse_produce_decision()` currently returns four fields,
including a redundant GPS surface, while `place_production_cell()` expects
`surface`, `item`, `hint`, plus keyword `requesting_player`. Step 3 must reconcile
that shape rather than blindly splatting the parser result. Preserve deterministic
failure acknowledgments and never replay Phase 2.

Fluid-capable layouts, Aquilo heat infrastructure, and an independent read-only
post-mutation success check also remain deliberately unimplemented.

The user explicitly wants a fresh context before any more production-cell work.
Do not begin Step 3 without renewed confirmation in that fresh context.

### Alert awareness

`ALERT_AWARENESS.md` remains a design only. Implementation is on hold behind the
production-cell work.

## Operational Caveats

- Do not restart Jimbo or Factorio merely to resume work. PID `211363` is stale;
  diagnose the unexplained stop or obtain user direction before starting a new
  Jimbo process.
- Use the detached launch procedure in `OPERATIONS.md` and verify the new PID
  from a separate command session.
- Do not delete hidden `/tmp` libraries without first fingerprinting exact
  targets and confirming no process has them open.
- Do not run live `test_ollama.py` while the Factorio client is using the GPU.
- Credentials, logs, PID/state files, player data, and local caches remain
  ignored and must not be staged.

## Natural Next Action

In the fresh context, first verify the stopped Jimbo runtime separately and ask
whether the user wants it diagnosed or restarted. Then ask whether to proceed
with Step 3. Once confirmed, wire the existing parser and placement helper into
classification, dispatch, and reply composition exactly as constrained by
`PROD_CELL_PLACE.md`, then test the full chat flow without broadening into
Steps 4–6.
