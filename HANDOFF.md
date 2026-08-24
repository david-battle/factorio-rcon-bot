# Handoff

## Verified State

- Branch `main`; local commits only (the user pushes manually). The tracked
  worktree is clean after this session's commit; the changes are captured in
  the handoff commit (pending the user's manual push).
- **Jimbo is RUNNING** (PID from `jimbo.pid`, `python -u jimbo.py`, gitignored
  `jimbo.log`), restarted 2026-08-24 with all of this session's freeform
  placement fixes live. Leave it running unless the user says otherwise.
- `ai_profile_name = "deepseek"` (jimbo.py, top config block) — paid
  `deepseek-v4-flash` via OpenCode Zen; `server_owner` / `ai_profiles` stayed
  in that single block per the always-preserve rule.
- Factorio is up: RCON answers on `127.0.0.1:27015`, version `2.1.14`. Server
  log at `/mnt/d/factorio-server/server-console.log`.

## Completed Work (2026-08-24) — freeform/decorative ghost placement fixed end-to-end

The freeform path (belt art, names, pixel drawings, decorative structures like
castles) previously failed repeatedly. It now works: visible, buildable,
correctly-anchored player-force ghosts with a clickable GPS link. One commit.

- **`game.player` is client-only.** `lua_essentials.txt` + `generate_lua_reference.py`
  now tell the model `game.player` is nil over RCON; use `game.get_player()` /
  `game.players`. Without this the model could not compose server-side Lua.
- **Freeform routing.** Classifier guidance routes creative/freeform requests
  ("freeform", "best-guess", "like you wrote your name", decorative) to the
  general slash-command path, not rigid `PRODUCE`.
- **Position injection.** `query_player_location()` resolves the requesting
  player's live position+surface (read-only RCON) and injects it into the
  classification prompt so freeform commands can anchor on "my current
  location" with concrete coordinates.
- **GPS ping on placement.** `ensure_gps_ping` now also handles freeform
  `/silent-command`s that `create_entity`; guidance makes the model print the
  exact spot as `[gps=x,y,surface]` so replies carry a clickable link.
- **Enemy-force ghost bug (root cause).** `create_entity` without an explicit
  `force` defaults to the `enemy` force, so ghosts were invisible/non-buildable
  to players even though RCON saw them. Guidance now requires
  `force=game.forces.player`; stray enemy-force ghost castles at `15,-125` and
  `-96,-25` were cleaned up (verified 0 remain).
- **Startup-summary discipline.** `startup_change_summary` is a delta, not a
  running feature list: every edit REPLACES it with a concise 1-2 sentence
  description of only the new change; the durable history in
  `STARTUP_ANNOUNCEMENTS.md` grows, the live summary does not. Enforced in the
  jimbo.py comment, `AGENTS.md`, and `STARTUP_ANNOUNCEMENTS.md` maintenance.

## Validation Run

- `python -m py_compile jimbo.py` OK.
- `python -m pytest test_jimbo.py` — 206 passed, 51 subtests passed.
- `git diff --check` clean.
- Did NOT run live `test_ollama.py` (the Factorio client is using the GPU).
- Live verification done in-game by the owner (castle now visible/buildable)
  plus direct RCON checks by the assistant (ghost force/position/count).

## Operational Caveats

- **Server description update pending.** `/mnt/d/factorio-server/config/server-settings.json`
  now reads "We're just here for Jimbo chat bot development — casual tinkering
  and testing." Factorio reads it only at startup, so it is NOT live until the
  next server restart. The owner wanted to wait until fewer players are on.
  Restart the server (`docs/OPERATIONS.md` "Restart procedure") when the owner
  approves.
- Do not restart or stop Jimbo/Factorio as part of a handoff unless the user
  asks; leave the current running process alone.
- Only intentional files are staged. `rconpw`, `*.key`, `jimbo.log`, `jimbo.pid`,
  `jimbo_says.log`, `jimbo_commands.log`, `last_startup_summary.txt`,
  `backup_loop.*`, `known_players.txt`, `restart_server.py`, `new_game.py`, and
  `produce_jobs/` remain ignored/untracked (machine-local operator data).
- The old repository at
  `/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints` is reference
  material only; mine it for layout geometry, never treat it as authoritative.
- A live player hint: vanilla F4 debug `show-detailed-info` shows the cursor
  position, not the character; a client-side mod like GPS_personal tracks the
  character (no server-side action needed).

## Natural Next Action

- Start `FIX_PLAN.md` item 3 Step 3 (verified primitive library) — the roadmap
  and reference sources are already durable there; see also
  `docs/FUTURE_DIRECTIONS.md` direction 14 for freeform design-quality ideas.
  Item 6 (tech-level-aware placement) stays deferred until item 3 lands.
- Before the next server restart, apply the pending server-description change
  (caveat above). Then push this handoff commit (user pushes manually).
