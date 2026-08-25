# Handoff

## Verified State

- Branch `main`; local commits only (the user pushes manually). The tracked
  worktree is clean after this session's commit; the changes are captured in
  the handoff commit (pending the user's manual push).
- **Jimbo is RUNNING** (PID `5223`, `python -u jimbo.py`, gitignored
  `jimbo.log`) with the PRE-change code. A restart is needed to load the new
  worker prompt/routing, the widened constants, and the new startup summary.
  Do not restart unless the user says so.
- `ai_profile_name = "deepseek"` (jimbo.py, top config block) — paid
  `deepseek-v4-flash` via OpenCode Zen; `server_owner` / `ai_profiles` stay in
  that single block per the always-preserve rule.
- **Factorio `2.1.16`**. Server log at `/mnt/d/factorio-server/server-console.log`.

## Completed Work (2026-08-25)

Shipped FIX_PLAN items 7 and 8 (quality-aware counting + spawn-aware default
placement), then replanned item 3 per owner direction and landed its core
capability. All validated; see Validation Run.

### Items 7 & 8 (quality counting + spawn placement)
- Fixed Lua-idiom guidance in `generate_lua_reference.py` `RULES`; regenerated
  `lua_essentials.txt`; reconciled `docs/RCON_NOTES.md`; updated the startup
  announcement; removed items 7/8 from `FIX_PLAN.md`.

### Item 3 replan + code-authoring worker (the "coding agent goodness")
Per the 2026-08-25 owner replan, Jimbo does NOT port old-repo cells; he
composes layouts from scratch by WRITING a Python generator program that is
executed and iterated against — the coding-agent loop, replacing the old
"emit a static JSON blob" worker.

- **`layout_analysis.py`** (new): deterministic throughput/balance/quality
  tool (`analyze_layout`, `quality_chance_distribution`, bottleneck sizing).
- **`layout_helpers.py`** (new): library generated code imports — plan
  builders, reach constants, boxes, rotate, and `bank(...)`.
- **`run_layout_generator`** (jimbo.py): writes the model's `generator.py` +
  `facts.json` into the job subdir and runs it as a normal subprocess. Owner
  chose NO restrictive sandbox (code runs with Jimbo's own reach); only the
  generator's OUTPUT is gated by the deterministic validator.
- **`build_custom_plan_prompt`**: asks for a complete program that computes
  the layout from the free-text hint + facts and prints a plan dict to stdout;
  runtime errors and validator rejections are fed back each iteration.
- **Parallel-bank support**: the recipe is now set on every building matching
  the plan's primary crafting machine (not the placement search's `en`) —
  see jimbo.py:2271/2280/2289 — so a homogeneous bank gets its recipe on all
  machines. `bank(facts, name, count, row_x, row_y)` builds a full
  validator-ready bank (shared input belt -> one inserter per machine ->
  shared output belt -> pole per machine). Geometry verified for 3x3..5x5
  footprints, banks to 8 machines.

## Validation Run

- `python -m py_compile jimbo.py layout_analysis.py layout_helpers.py
  generate_lua_reference.py` clean.
- `python -m pytest -q test_jimbo.py` → **225 passed, 51 subtests passed**.
- `git diff --check` clean.
- Bank layout geometry checked ad hoc across `recycler`(4x4), `foundry`(5x5),
  `chemical-plant`(3x3), `electric-furnace`(3x3) at 8 machines: 0 validator
  errors each. No live RCON commands run.

## Operational Caveats

- `lua_essentials.txt` is generated from `generate_lua_reference.py` `RULES`;
  edit the source, never the `.txt`. Never commit `doc-html/runtime-api.json`.
- Generated design programs run as a subprocess in the job subdir with the
  same reach as Jimbo (owner's explicit choice, not a sandbox). The
  deterministic validator is the safety gate on whatever they output.
- `layout_analysis.py` module-effect/recipe values are INPUTS, pending server
  verification — not hardcoded assumptions.
- Version-stamped learnings in `docs/RCON_NOTES.md` /
  `docs/FUTURE_DIRECTIONS.md` may predate 2.1.16; re-verify before relying.
- `docs/ARCHIVE.md` is intentionally unreferenced; do not link it from live docs.
- Do not restart/stop Jimbo or Factorio as part of a handoff unless asked.
- Only intentional files are staged. `rconpw`, `*.key`, `jimbo.log`,
  `jimbo.pid`, `jimbo_says.log`, `jimbo_commands.log`,
  `last_startup_summary.txt`, `backup_loop.*`, `known_players.txt`,
  `restart_server.py`, `new_game.py`, and `produce_jobs/` remain
  ignored/untracked (machine-local operator data). Ollama stays a
  manually-selected alternative provider, never a dynamic fallback.
- Old repo `/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints` is
  reference-only; never authoritative.

## Natural Next Action

1. Broaden the still item-centric job framing to arbitrary designs (FIX_PLAN
   item 3 follow-on): the code-authoring loop is in place and geometry-general,
   but `query_production_cell_candidates` and the survey vocabulary still
   target an item. Make the survey hint-driven so any build (including
   defensive/combat structures) can be surveyed and stamped; keep the
   validator as-is.
2. Mechanically invoke `layout_analysis` each worker iteration (the proposal
   schema must first carry module/recipe flow inputs) — currently described in
   the prompt and importable by generators, but not fed back per-iteration.
3. Then push this handoff commit (user pushes manually).
