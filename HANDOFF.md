# Handoff

## Verified State

- Branch `main`; local commits only (the user pushes manually). The tracked
  worktree is clean after this session's commit; the changes are captured in
  the handoff commit (pending the user's manual push).
- **Jimbo is RUNNING** (PID `5223`, `python -u jimbo.py`, gitignored
  `jimbo.log`), restarted 2026-08-24 so he loads this session's prompt/routing
  and Lua-reference changes. Leave it running unless the user says otherwise.
- `ai_profile_name = "deepseek"` (jimbo.py, top config block) — paid
  `deepseek-v4-flash` via OpenCode Zen; `server_owner` / `ai_profiles` stayed
  in that single block per the always-preserve rule.
- **Factorio `2.1.16`** (unchanged from last handoff). Server log at
  `/mnt/d/factorio-server/server-console.log`.

## Completed Work (2026-08-24) — Jimbo reliability + tech-aware placement

One commit. This session was triggered by live chat failures: Jimbo gave wrong
lookup answers, errored on a recipe/chart-tag query, and placed a locked
Electromagnetic Plant for Speed Module 2.

- **Lua reference gotchas.** Added to `generate_lua_reference.py` `RULES`
  (source of truth) and regenerated `lua_essentials.txt`: recipe is read via
  the method `entity.get_recipe()` (no `recipe` field, which RAISES); chart
  tags use `game.forces.player.add_chart_tag(...)`, not `create_chart_tag`.
  This file is injected into both the lookup and classification prompts, so the
  model no longer invents those member names.
- **Lookup routing.** In `build_classification_prompt`, LOGISTICS is now
  reserved for the player's actual logistic network; "in storage", "stash",
  "where is X kept/stored", "in a chest/container/box" explicitly route to
  LOOKUP. `build_lookup_prompt` now instructs the composed Lua to list matching
  container positions as `[gps=x,y,surface]` when a question asks where.
- **Tech-aware placement.** `place_production_cell`'s phase1 Lua now filters
  compatible crafting machines to those the player has actually researched:
  it builds the craftable-item set from `pairs(game.forces.player.recipes)`
  where `r.enabled`, keeps machines whose `items_to_place_this[1]` is in that
  set, and only falls back to the full list when none is researched (so
  placement never hard-fails). A locked Electromagnetic Plant is no longer
  chosen for Speed Module 2.
- **Custom-cell worker.** `query_production_cell_candidates` (the probe shared
  by both the standard path and the `layout=custom` worker's site survey) got
  the same research filter, so `facts["machines"]` only lists researched
  machines and the worker can only propose them. Defense in depth: the probe
  filters, and phase1 filters again on placement.
- **Announcement discipline.** `startup_change_summary` replaced and its exact
  text appended to `STARTUP_ANNOUNCEMENTS.md` for the player-visible lookup
  routing and tech-aware placement changes.
- **Durable learning.** Added the research-gating idiom
  (`LuaRecipe.enabled` + `items_to_place_this`) to `docs/RCON_NOTES.md`.

## Validation Run

- `python -m py_compile jimbo.py generate_lua_reference.py` OK.
- `python -m pytest test_jimbo.py` — 208 passed, 51 subtests passed. New tests:
  `test_place_cell_filters_machines_to_researched_unlocks` (phase1),
  `test_probe_filters_machines_to_researched_unlocks` (probe), and updated
  classifier-routing assertions for LOGISTICS vs LOOKUP.
- `git diff --check` clean.
- Did NOT run live `test_ollama.py` (the headful Factorio client is using the
  GPU) and did not run live RCON Lua (no authority to run commands against the
  live server; the new Lua is read-only and mirrors an already-working idiom).

## Operational Caveats

- `lua_essentials.txt` is a generated artifact; edit its source
  `generate_lua_reference.py` `RULES` block and regenerate — do not edit the
  `.txt` by hand. Never commit the source `doc-html/runtime-api.json`.
- Version-stamped learnings in `docs/RCON_NOTES.md` / `docs/FUTURE_DIRECTIONS.md`
  may predate 2.1.16; re-verify before relying on them (see RCON_NOTES header).
- Do not restart/stop Jimbo or Factorio as part of a handoff unless asked; the
  running process (PID 5223) should be left alone.
- Only intentional files are staged. `rconpw`, `*.key`, `jimbo.log`,
  `jimbo.pid`, `jimbo_says.log`, `jimbo_commands.log`,
  `last_startup_summary.txt`, `backup_loop.*`, `known_players.txt`,
  `restart_server.py`, `new_game.py`, and `produce_jobs/` remain
  ignored/untracked (machine-local operator data).
- The old repo at
  `/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints` is reference
  material only; never treat it as authoritative.

## Natural Next Action

- Confirm the tech-aware placement fix live on the running server (e.g. ask
  Jimbo for a Speed Module 2 cell before EM plants are researched) and check
  `jimbo.log` / the console log for the placed machine. The unchanged runtime
  API is 2.1.16.
- FUTURE_DIRECTIONS item 14 quality work remains partially open: the custom
  cell now picks a researched machine, but the "prefer longer through-connected
  lanes" and "balanced inserter direction" ideas are still unimplemented.
- Then push this handoff commit (user pushes manually).
