# Handoff

## Verified State

- Branch `main`; local commits only (the user pushes manually). The tracked
  worktree is clean after this session's commit; the changes are captured in
  the handoff commit (pending the user's manual push).
- **Jimbo is RUNNING** (PID `5223`, `python -u jimbo.py`, gitignored
  `jimbo.log`), restarted 2026-08-24 so he loads the 08-24 prompt/routing and
  Lua-reference changes. Leave it running unless the user says otherwise.
- `ai_profile_name = "deepseek"` (jimbo.py, top config block) — paid
  `deepseek-v4-flash` via OpenCode Zen; `server_owner` / `ai_profiles` stay in
  that single block per the always-preserve rule.
- **Factorio `2.1.16`** (unchanged from last handoff). Server log at
  `/mnt/d/factorio-server/server-console.log`.

## Completed Work (2026-08-25) — Overnight interaction triage + two RCON/Lua fix items

This session was triage, not code. I reviewed the overnight chat
(2026-08-24 21:00 → 2026-08-25 07:30) in the server console log plus
`jimbo_says.log` / `jimbo_commands.log` for Jimbo interaction data, then turned
the two real Lua bugs found into documented fix-plan items and durable notes.
One commit; doc-only, no player-visible behavior change.

- **FIX_PLAN items 7 and 8** appended (both standalone, no dependencies on
  preceding items):
  - **7 — `LuaInventory.get_item_count` rejects a quality argument.**
    `get_item_count("solar-panel","rare")` failed live (2026-08-25 04:34,
    Koopix's rare solar/accumulator scan across non-nauvis surfaces) with
    "Expected 0 or 1 arguments but 2 were given". Fix: iterate
    `get_contents()` and match on `name`/`quality`.
  - **8 — Map-tag placement fails on surface spawn lookup.**
    `game.surfaces["nauvis"].spawn_position` and `.spawn` both raise
    "doesn't contain key" (darklich14's map-tag request, 2026-08-25 04:08-04:09).
    Spawn coords live on map settings, not the surface object. Fix: read them
    from map settings and update prompt guidance.
- **docs/RCON_NOTES.md hints** added for both (get_item_count quality overload
  extends the existing 2.1.14 name-arg note; LuaSurface has no spawn key).

## Validation Run

- `git diff --check` clean.
- No code changed this session, so no `py_compile`/`pytest` run. No live RCON
  commands run (no authority to act on the live server); both findings are
  already recorded live failures.

## Operational Caveats

- `lua_essentials.txt` is a generated artifact; edit its source
  `generate_lua_reference.py` `RULES` block and regenerate — do not edit the
  `.txt` by hand. Never commit the source `doc-html/runtime-api.json`.
- Version-stamped learnings in `docs/RCON_NOTES.md` /
  `docs/FUTURE_DIRECTIONS.md` may predate 2.1.16; re-verify before relying on
  them (see RCON_NOTES header).
- Do not restart/stop Jimbo or Factorio as part of a handoff unless asked; the
  running process (PID 5223) should be left alone.
- Only intentional files are staged. `rconpw`, `*.key`, `jimbo.log`,
  `jimbo.pid`, `jimbo_says.log`, `jimbo_commands.log`,
  `last_startup_summary.txt`, `backup_loop.*`, `known_players.txt`,
  `restart_server.py`, `new_game.py`, and `produce_jobs/` remain
  ignored/untracked (machine-local operator data). Ollama stays a
  manually-selected alternative provider (set `ai_profile_name = "ollama"`),
  never a dynamic fallback.
- The old repo at
  `/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints` is reference
  material only; never treat it as authoritative.

## Natural Next Action

- Implement FIX_PLAN items 7 and 8: make quality-specific container counts
  iterate `get_contents()` (item 7), and make default-location map tags read
  spawn from map settings rather than `surface.spawn*` (item 8). Both are
  standalone Lua-idiom fixes; fold the working idiom into `docs/RCON_NOTES.md`
  in the same edit.
- FIX_PLAN item 3 Step 3 (verified primitive library) remains the larger
  next step; item 6 (tech-aware placement) stays deferred until item 3 lands.
- Then push this handoff commit (user pushes manually).
