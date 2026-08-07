# Handoff

## Verified State

- Branch: `main`; local commits only (the user pushes manually).
- **Jimbo is NOT running.** `jimbo.pid` is stale; no `jimbo.py` process is alive.
  Factorio is up: RCON answers on `127.0.0.1:27015` and `/version` reports
  `2.1.14`.
- Jimbo's configured profile is still `free-models-router` (OpenRouter
  `openrouter/free` via `https://openrouter.ai/api/v1`, reading
  `openrouter.key`; never read or print a key). Nothing in `jimbo.py` changed
  this session.
- The backup loop is stopped: no `backup_loop.py` process is alive. The two most
  recent backups remain in `/mnt/d/factorio-server/saves/archive/` (`...06-50-22`
  and `...06-39-37`); the other 30 were reaped on request.

## Completed Work

### Overnight backup loop (this session)

- Added `backup_loop.py` (repo root): every 15 minutes it runs `/server-save`
  via RCON, copies the live save to
  `/mnt/d/factorio-server/saves/archive/New Space Age Server backup
  <timestamp>.zip`, verifies the copy's size, and never overwrites an existing
  archive file. Failures are logged and the loop keeps trying next interval.
- Ran unattended overnight (first backup 01:09, last 06:39, ~24 archives), then
  stopped on request.
- `docs/OPERATIONS.md`: added "Quick Backup Copy" (run `/server-save` via RCON
  first, then copy + verify) and "Overnight Backup Loop" (launch/stop commands)
  under Save Checkpoints.
- `.gitignore`: added `backup_loop.py`, `backup_loop.log`, `backup_loop.pid`
  — machine-local operator tooling, matching the existing `restart_server.py` /
  `new_game.py` treatment.

### Other notes

- Sent a server-wide in-game acknowledgment over direct RCON as "Big Pickle"
  (assistant action, not Jimbo) using `/silent-command game.print(...)`, which
  RCON_NOTES already documents as not appearing in `server-console.log`.

## Validation

- `python -m py_compile backup_loop.py` clean.
- `python -m pytest test_jimbo.py -q`: **127 passed, 43 subtests passed**.
- `git diff --check` clean.
- Not run: `test_ollama.py` (per operations guidance, avoid while the Factorio
  client uses the GPU).

## Remaining Work

- Restart Jimbo when the user asks (it is currently down). Follow
  `docs/OPERATIONS.md`; ensure the stale process is gone before relaunching.
- Re-verify 2.1.14-sensitive RCON/Lua API facts before relying on them;
  `docs/RCON_NOTES.md` still documents 2.1.12-era behavior.

## Operational Caveats

- `backup_loop.py` is gitignored like the other operator scripts but lives at
  repo root; the docs reference it. Keep the script and OPERATIONS.md in sync if
  paths or the interval change.
- Factorio save backups and the overnight run are server-adjacent work; the bot
  and its profile configuration are unchanged.
- Only stage intentional changes. `*.key`, `rconpw`, `jimbo.log`, `jimbo.pid`,
  `jimbo_says.log`, `backup_loop.*`, `last_*.txt`, `known_players.txt`,
  `restart_server.py`, `new_game.py` remain ignored/untracked (machine-local
  operator data).

## Natural Next Action

- Restart Jimbo (user-triggered; it is down). Then review and push the handoff
  commit.
