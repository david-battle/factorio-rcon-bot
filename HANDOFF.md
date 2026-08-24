# Handoff

## Verified State

- Branch `main`; local commits only (the user pushes manually). The tracked
  worktree is clean after this session's commit; the changes are captured in
  the handoff commit (pending the user's manual push).
- **Jimbo is RUNNING** (PID from `jimbo.pid`, `python -u jimbo.py`, gitignored
  `jimbo.log`), restarted 2026-08-24 with all of this session's Step 2 changes
  live. Leave it running unless the user says otherwise.
- `ai_profile_name = "deepseek"` (jimbo.py, top config block) — paid
  `deepseek-v4-flash` via OpenCode Zen, reading the `opencode` credential from
  `~/.local/share/opencode/auth.json`; never read or print a token. The
  `server_owner` / `ai_profiles` values stayed in that single block per the
  always-preserve rule.
- Factorio is up: RCON answers on `127.0.0.1:27015`, version `2.1.14`. Server
  log at `/mnt/d/factorio-server/server-console.log`.

## Completed Work (2026-08-24, FIX_PLAN item 3 Steps 1 + 2)

Step 1 (parameterized layouts) shipped earlier and is now live; Step 2 (the
custom-cell worker subprocess) was implemented this session, shipped, and
live-validated. All changes share one commit.

### Step 2 — Custom-cell worker subprocess

The open-ended layout path (`layout=custom` and the structural-fallback path)
now runs as an async detached worker instead of refusing inline. See
`docs/BOT_CONTRACTS.md` "Custom-cell worker (async)" for the full contract and
`docs/RCON_NOTES.md` "Custom-cell worker (Step 2) Lua learnings" for the live
prototype facts.

- **Trigger (both paths):** classifier `layout=custom`, and Python fallback
  when the pre-planned variant exhausts every anchor with no structurally
  placeable candidate (not the support fallback, which already succeeds).
- **Job store:** gitignored `produce_jobs/<id>/` (`job.json`, `status.json`,
  `result.json`, `worker.log`) so a restart can reap dead workers and report
  unfinished work. Chunk-based dedupe (surface + item + rounded GPS origin)
  suppresses duplicate jobs while one is pending/running.
- **Worker:** `python jimbo.py --produce-worker <job.json>` (argv branch at the
  `__main__` guard, before RCON). NO RCON connection; the parent surveys the
  site read-only before forking. Budgets: 1h wall clock + 15-iteration cap.
  Returns a JSON entity-offset table in the exact schema Step 1 stamps.
- **Deterministic validator:** `validate_custom_cell_plan` checks schema,
  prototype existence, footprint overlap, inserter pickup/drop reach (regular
  1.00/1.20, long-handed 2.00/2.20), connected belt lanes of ≥2 tiles, pole
  supply coverage (Chebyshev), building count = 1, and pole/req flag
  consistency. Rejections feed back verbatim to the model next iteration.
- **Stamping:** parent re-validates, `_normalize_custom_variant` centers the
  building at its own footprint, then stamps through the existing Phase 2
  mutation path (all-or-nothing, full rollback).
- **Chat flow:** one immediate `PENDING:` ack (never claims placement), then
  exactly one truthful completion report. `JOBSTATUS` ("what are you
  building?") reads stored job state and answers literally. Reply-honesty
  rules apply to both ack and completion.

### Wiring

- `dispatch_production_cell` routes `layout=custom` and the
  "No suitable production-cell location within" fallback to
  `maybe_start_custom_cell_job`; `poll_produce_jobs` runs alongside
  `maybe_spontaneous` in the idle tick (5s interval) and at startup;
  `parse_job_status_decision` added to the recognized/classifier set.
- `place_production_cell` accepts an optional `custom_variant` knob key (the
  only legal extra key beyond the default knob set).
- Classifier and reply prompts extended: `layout=custom` in the knob docs,
  `JOBSTATUS` verb, and PENDING/status honesty hints.

### Docs

- `docs/BOT_CONTRACTS.md`: `custom` in the knob table, custom-cell worker
  contract, and the free-form ghost-composition preservation directive.
- `docs/RCON_NOTES.md`: Step 2 Lua learnings (footprint offsets, survey
  commands, pole reach reads, recipe ingredients, worker-never-RCON).
- `docs/FUTURE_DIRECTIONS.md`: direction 13 (belt-fed is a pre-bot capability)
  and direction 14 (custom-cell worker design quality).
- `FIX_PLAN.md`: item 3 Steps 1 and 2 marked shipped/live-validated; execution
  order updated (Step 3 next).
- `startup_change_summary` + `STARTUP_ANNOUNCEMENTS.md` updated (player-visible
  custom-cell announcement) in the same edits per the always-preserve rule.

## Live Validation (2026-08-24)

Confirmed on the live server after restart:

- A `layout=custom` copper-cable request (standing) spawned a detached worker
  (PID 85332, tracked, no RCON), with a truthful `PENDING:` ack.
- A concurrent free-form belt-fed placement request placed ghosts immediately
  at `[gps=-100,-17,nauvis]` and did NOT dedupe against the running custom
  job — the two ran independently (the intended concurrency behavior).
- `JOBSTATUS` answered from stored state across three checks: "iteration 1",
  then "iteration 2 / 6m48s", then "no custom cell designs in progress".
- The custom worker accepted a 2-iteration design (assembling-machine-1,
  inserter, 2 belt, medium-electric-pole), which was re-validated, normalized,
  stamped via Phase 2 at `[gps=-107,-15,nauvis]`, and reported truthfully with
  the WARNINGs. Final status `done_placed`, `reported=true`; worker exited
  cleanly; `result.json` holds the accepted variant.

## Validation Run

- `python -m py_compile jimbo.py test_jimbo.py` OK.
- `python -m pytest test_jimbo.py` — 205 passed, 51 subtests passed.
- `git diff --check` clean.
- Did NOT run live `test_ollama.py` (the Factorio client is using the GPU).
- Live RCON verification above was performed in-game by the owner.

## Operational Caveats

- Only intentional files are staged. `*.key`, `rconpw`, `jimbo.log`,
  `jimbo.pid`, `jimbo_says.log`, `jimbo_commands.log`, `backup_loop.*`,
  `last_*.txt`, `known_players.txt`, `restart_server.py`, `new_game.py`, and
  `produce_jobs/` remain ignored/untracked (machine-local operator data).
- Do not restart or stop Jimbo/Factorio as part of a handoff unless the user
  asks; leave the current running process alone.
- The old repository at
  `/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints` is reference
  material only (owner's explicit instruction): mine it for layout geometry
  and generate-validate-test patterns; never treat its content as
  authoritative or import its framework.
- The live custom-cell design was functional but basic (base machine, short
  2-belt tail) — a quality/optimization matter, not a scaffolding defect. See
  `FUTURE_DIRECTIONS` direction 14 for the improvement sketch; do not treat it
  as a blocker.

## Natural Next Action

- Start `FIX_PLAN.md` item 3 Step 3 (verified primitive library): compose
  layouts from primitives that have each earned trust via tests (straight bus,
  tap-in inserter, chest drop, lane pair), and port candidates from the old
  reference repo. Optionally fold in the Step 2 design-quality improvements
  from `FUTURE_DIRECTIONS` direction 14. Then push this handoff commit (user
  pushes manually).
