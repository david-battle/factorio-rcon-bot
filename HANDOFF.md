# Handoff

## Verified State

- Branch `main`; local commits only (the user pushes manually). The tracked
  worktree is clean after this session's commit; the changes are captured in
  the handoff commit (pending the user's manual push).
- **Jimbo is RUNNING** (PID from `jimbo.pid`, `python -u jimbo.py`, gitignored
  `jimbo.log`), restarted 2026-08-24 after the 2.1.16 upgrade so he loads the
  freshly regenerated `lua_essentials.txt`. Leave it running unless the user
  says otherwise.
- `ai_profile_name = "deepseek"` (jimbo.py, top config block) — paid
  `deepseek-v4-flash` via OpenCode Zen; `server_owner` / `ai_profiles` stayed
  in that single block per the always-preserve rule.
- **Factorio upgraded to `2.1.16`** this session. The `current` junction in
  `/mnt/d/factorio-standalone/` points at `Factorio_2.1.16`; `2.1.15` is kept
  as rollback, `2.1.14` was removed. RCON answers on `127.0.0.1:27015` and
  `/version` reports `2.1.16`. Server log at
  `/mnt/d/factorio-server/server-console.log`.

## Completed Work (2026-08-24) — Factorio 2.1.16 upgrade

One commit. Followed `docs/OPERATIONS.md` "Upgrade The Game Version" end to end:

- **Download + verify.** `factorio-space-age_win_2.1.16.zip` fully downloaded
  (`Unconfirmed *.crdownload` was left alone until it became the named zip);
  `~/.local/usr/bin/unzip -l` confirmed root `Factorio_2.1.16/` (20,833 files)
  and a background `-t` passed with no errors.
- **Extract.** Windows `tar.exe -xf ... -C D:\factorio-standalone`; verified
  `bin/x64/factorio.exe` and `data/base/info.json` = `2.1.16`.
- **Junction.** Removed the old `current` junction, then
  `cmd.exe /c "mklink /J D:\factorio-standalone\current D:\factorio-standalone\Factorio_2.1.16"`;
  verified with `cmd /c dir /a` and that `current/bin/x64/factorio.exe`
  resolves.
- **Cleanup.** Removed `Factorio_2.1.14/` and the stale 2.1.15 zip after the
  new version confirmed running; kept `Factorio_2.1.15/` as rollback.
- **Restart.** Launched `D:\ss.bat`; `/version` returns `2.1.16`.
- **Reference regen.** `python generate_lua_reference.py` rewrote
  `lua_essentials.txt` (6,459 chars) from the 2.1.16 docs; Jimbo restarted so
  he loads it. Diff was a clean regeneration (gained `LuaItemGroup` /
  `LuaItemSubGroup`, dropped `LuaGroup`).
- **Docs.** `docs/OPERATIONS.md` version reference (Environment + upgrade
  examples/file counts) updated to 2.1.16; `docs/RCON_NOTES.md` header now says
  2.1.16 and notes that version-stamped learnings may predate it; a stale
  `application_version` mention in `docs/FUTURE_DIRECTIONS.md` updated.
- **Server-description change live.** The pending
  `/mnt/d/factorio-server/config/server-settings.json` description ("We're just
  here for Jimbo chat bot development — casual tinkering and testing") is now
  active since the server restarted (Factorio reads it only at startup).
- Server + Jimbo were cleanly stopped before the upgrade and restarted after.

## Validation Run

- `python -m py_compile jimbo.py restart_server.py new_game.py backup_loop.py
  generate_lua_reference.py` OK.
- `python -m pytest test_jimbo.py` — 206 passed, 51 subtests passed.
- `git diff --check` clean.
- No code changed this session (prompt data + docs only), so the passing suite
  reflects prior code. Live `/version` confirmed `2.1.16`. Did NOT run live
  `test_ollama.py` (the headful Factorio client is using the GPU).

## Operational Caveats

- The 2.1.12/2.1.14 learnings still in `docs/RCON_NOTES.md`,
  `docs/FUTURE_DIRECTIONS.md`, and `docs/OPERATIONS.md` are historical,
  stamped with the version they were verified on; do not rewrite them into
  2.1.16 claims unless re-verified. The header of `RCON_NOTES.md` now says to
  re-verify version-sensitive behavior after an upgrade.
- `lua_essentials.txt` is a generated artifact from the current install; never
  commit the source `doc-html/runtime-api.json` (per OPERATIONS).
- Do not restart or stop Jimbo/Factorio as part of a handoff unless the user
  asks; leave the current running process alone.
- Only intentional files are staged. `rconpw`, `*.key`, `jimbo.log`, `jimbo.pid`,
  `jimbo_says.log`, `jimbo_commands.log`, `last_startup_summary.txt`,
  `backup_loop.*`, `known_players.txt`, `restart_server.py`, `new_game.py`, and
  `produce_jobs/` remain ignored/untracked (machine-local operator data).
- The old repository at
  `/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints` is reference
  material only; mine it for layout geometry, never treat it as authoritative.

## Natural Next Action

- Start `FIX_PLAN.md` item 3 Step 3 (verified primitive library) — the roadmap
  and reference sources are already durable there; see also
  `docs/FUTURE_DIRECTIONS.md` direction 14 for freeform design-quality ideas.
  Item 6 (tech-level-aware placement) stays deferred until item 3 lands.
- Next on the ops track: the Factorio 2.1.16 runtime API is the current
  authority; re-verify any 2.1.14-stamped RCON/Lua learning before relying on
  it (see RCON_NOTES header). Then push this handoff commit (user pushes
  manually).
