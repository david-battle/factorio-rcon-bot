# Handoff

## Verified State

- Branch: `main`; local commits only (the user pushes manually).
- **Jimbo is NOT running.** `jimbo.pid` is stale (holds `368605`); no
  `jimbo.py` process is alive. Do not trust the previous handoff's "running"
  claim. Factorio is up: RCON answers on `127.0.0.1:27015` and `/version`
  reports `2.1.14`.
- Jimbo's configured profile is `free-models-router` (OpenRouter `openrouter/free`
  via `https://openrouter.ai/api/v1`, reading `openrouter.key`; never read or
  print a key). `max_completion_tokens: 256`, reasoning excluded.
- The Free Models Router startup announcement already broadcast:
  `last_startup_summary.txt` matches `startup_change_summary`, so no
  announcement is pending for the next restart.

## Completed Work

### Factorio 2.1.14 upgrade (this session)

- Server upgraded from 2.1.12 to experimental 2.1.14. New install extracted
  from `factorio-space-age_win_2.1.14.zip` (verified intact) into
  `/mnt/d/factorio-standalone/Factorio_2.1.14/`; `current` junction repointed
  via `mklink /J`; `/version` rechecked = 2.1.14; log reopened; dlbattle
  connected. Steps are documented in `docs/OPERATIONS.md` under
  "Upgrade The Game Version".
- Cleaned up ~14 GB: removed `Factorio_2.1.11` tree, `factorio-standalone-latest.zip`,
  `_extract_temp`, and the empty `Downloads/factorio-space-age_win_2.1.12` dir
  and its 4.6 GB zip. `Factorio_2.1.12/` tree kept as rollback per the updated
  rollback policy in OPERATIONS.md.
- `docs/OPERATIONS.md`: added unzip location note (`~/.local/usr/bin/unzip`, not
  on PATH), the Upgrade The Game Version procedure, and the revised rollback
  policy. WSL `unzip` is too slow for extraction over the 9P mounts; use Windows
  `tar.exe`.

### Free Models Router switch (carried over, previously uncommitted)

- `jimbo.py`: `ai_profile_name` is now `free-models-router`; the `groq` profile
  was removed, `free-models-router` added (OpenRouter adapter, `openrouter.key`),
  `ollama` reordered. `startup_change_summary` updated; appended to
  `STARTUP_ANNOUNCEMENTS.md` under 2026-08-05.
- `docs/OPERATIONS.md`: provider table, provider history, and Groq section
  updated to match.
- `docs/FUTURE_DIRECTIONS.md`: alerts snapshot function and spontaneous-prompt
  inclusion marked done.

### Test updates for the profile change

- `test_jimbo.py`: the three `groq`-referencing tests were failing (the profile
  was removed without updating tests). Updated the profile set assertion,
  adapter-selection case, and rewrote the key-file/hidden-reasoning adapter test
  to target `free-models-router` (openrouter.key, OpenRouter base URL,
  `openrouter/free`, 256 tokens, `include_reasoning`/`reasoning_effort`).

## Validation

- `python -m py_compile jimbo.py` clean; `git diff --check` clean.
- `python -m pytest test_jimbo.py -q`: **127 passed, 43 subtests passed**.
- Not run: `test_ollama.py` (per operations guidance, avoid while the Factorio
  client uses the GPU).
- RCON verified live: `/version` = 2.1.14, `/players` = dlbattle online.

## Remaining Work

- Restart Jimbo when the user asks (it is currently down). Follow
  `docs/OPERATIONS.md`; ensure the stale process is gone before relaunching.
- Re-verify 2.1.14-sensitive RCON/Lua API facts before relying on them:
  `docs/RCON_NOTES.md` still documents 2.1.12 behavior, and the 2.1.14 API
  surface is unverified.

## Operational Caveats

- 2.1.14 is experimental; `Factorio_2.1.12/` is the rollback tree. Flip the
  `current` junction back and restart via `D:\ss.bat` if 2.1.14 misbehaves.
- The server console log reopened at 13:58 and `/version`/`/players` respond;
  if Jimbo is restarted it will tail it normally.
- Only stage intentional changes. `*.key`, `rconpw`, `jimbo.log`, `jimbo.pid`,
  `jimbo_says.log`, `last_*.txt`, `known_players.txt`, `restart_server.py`,
  `new_game.py` remain ignored/untracked (machine-local operator data).

## Natural Next Action

- Restart Jimbo (user-triggered; it is down). Then review and push the handoff
  commit.
