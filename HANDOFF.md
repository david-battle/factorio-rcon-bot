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

## Completed Work (2026-08-25) — Documentation cruft archived

Doc-only session, no code change. To reduce context bloat, no-longer-relevant
historical content was moved out of the live docs into `docs/ARCHIVE.md`
(564 lines), which NO live `.md` file links to; a future context opens it only
if explicitly pointed there. `git diff --check` clean.

- Created `docs/ARCHIVE.md` with archived retrospectives and experiment
  write-ups sectioned by source.
- `FIX_PLAN.md` (175 → 79): kept only active items (3 Step 3, 6, 7, 8) plus a
  one-line status header; shipped item 3 Steps 1–2 retrospectives archived.
- `docs/FUTURE_DIRECTIONS.md` (772 → 314): kept intro + directions 1–14;
  "Alert Awareness Design" and all "Tested Implementation Findings" archived
  (their features are implemented and documented in `BOT_CONTRACTS.md`).
- `docs/OPERATIONS.md` (494 → 475): removed "Provider History" and "Groq"
  (archived); also recorded the 2026-08-25 live `/version`=2.1.16 recheck.
- `AGENTS.md`: noted `CLAUDE.md` is a tracked symlink to `AGENTS.md` so it
  stops surfacing as a separate file.
- Untouched by agreement: `STARTUP_ANNOUNCEMENTS.md`, `docs/RCON_NOTES.md`,
  `docs/BOT_CONTRACTS.md`.

## Validation Run

- `git diff --check` clean.
- No code changed this session, so no `py_compile`/`pytest` run. No live RCON
  commands run (none needed; the earlier `/version` recheck is already
  recorded in OPERATIONS).

## Operational Caveats

- `lua_essentials.txt` is a generated artifact; edit its source
  `generate_lua_reference.py` `RULES` block and regenerate — do not edit the
  `.txt` by hand. Never commit the source `doc-html/runtime-api.json`.
- Version-stamped learnings in `docs/RCON_NOTES.md` /
  `docs/FUTURE_DIRECTIONS.md` may predate 2.1.16; re-verify before relying on
  them (see RCON_NOTES header).
- `docs/ARCHIVE.md` is intentionally unreferenced; do not add links to it from
  live docs. The user points future contexts at it manually only if needed.
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
