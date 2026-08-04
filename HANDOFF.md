# Handoff

## Verified State

- Branch: `main`; local commits only (the user pushes manually).
- **Jimbo is running** under pid `357147` (see `jimbo.pid`), verified alive
  (uptime 09:00:29). The launcher via `setsid` forks, so re-confirm the
  recorded PID with `ps` from a fresh session.
- **Jimbo runs on `big-pickle`** via OpenCode Zen (OpenAI-compatible,
  `https://opencode.ai/zen/v1`, `auth_provider=opencode` reading
  `~/.local/share/opencode/auth.json`; never read or print a token),
  `max_completion_tokens: 4096`.
- `last_startup_summary.txt` matches the current `startup_change_summary`
  ("I now remember about 40 minutes of recent chat instead of 15..."), so no
  further `STARTUP_ANNOUNCEMENTS.md` entry is needed. `jimbo.py` was not
  edited this session, so no startup-summary bump was warranted.
- All tracked changes are committed; the tracked worktree is clean. Pending
  the user's manual push.

## Completed Work

### Server ops tooling (this session)

Requested to help run the server from WSL and prepare restart / fresh-world
scripts.

- Added `restart_server.py` and `new_game.py` (repo root, **intentionally
  untracked** and gitignored — see below). Both are local operator scripts,
  not repository source.
  - `restart_server.py`: sends `/quit` over RCON, waits for shutdown, reaps
    the old `rcon.exe` console via PowerShell, relaunches `D:\ss.bat`,
    verifies RCON answers. Prompts for confirmation; `-y` skips prompts.
  - `new_game.py`: stops the server, moves the live save
    `New Space Age Server.zip` to
    `archive/pre-newgame-YYYY-MM-DD_HH-mm-ss.zip` (never overwrites;
    auto-suffixes on collision), launches `D:\ss.bat` to auto-create a fresh
    world, reseeds `known_players.txt`, verifies the new save and RCON.
  - Neither script prints the RCON password (read from
    `/mnt/d/factorio-server/config/rconpw`); both use the `/mnt/d/.venv`
    `rcon` package (system python3 has no rcon).
  - **Not yet executed.** The user said "Don't do it now" for the restart;
  `new_game.py` was requested but never run. Both are still to be tested
  against the live server.
- `.gitignore`: added `restart_server.py` and `new_game.py` (durable ignore
  rule for these local artifacts).
- `docs/OPERATIONS.md` additions:
  - Restart procedure (RCON `/quit` → `:q` → `D:\ss.bat`) plus the automated
    WSL variant (RCON quit, reap `rcon.exe`, `Start-Process D:\ss.bat`,
    verify).
  - "Start A New Game" section: clean stop → archive live save (never
    overwrite) → verify live path empty → `D:\ss.bat` auto-creates fresh
    world → reseed `known_players.txt` from `/players` → verify.
  - "Server Pauses With No Players Online" runtime pitfall: zero-player idle
    pause (time frozen, no autosaves, ~1 tick/10s) is normal, not a hang;
    judge liveness by RCON + resumed world on `[JOIN]`, not frozen time.

## Validation

- `python -m py_compile jimbo.py` clean; `git diff --check` clean.
- `python -m py_compile restart_server.py new_game.py` clean (venv python).
- `python -m pytest test_jimbo.py -q`: **127 passed, 43 subtests passed**.
- Not run: `test_ollama.py` (per operations guidance, avoid while the Factorio
  client uses the GPU).
- Not run: the restart/new-game scripts themselves — never executed, pending
  the user's go-ahead.

## Remaining Work

- **Test the scripts live** when the user allows. Run `restart_server.py` and
  confirm the old RCON console is reaped and a fresh one opens; then, if the
  user wants, test `new_game.py` (destructive — requires archiving the current
  world; only with explicit confirmation).
- Residual limitation (from prior handoffs, unchanged): `TAG` cannot filter
  assembling machines by current recipe. See `docs/FUTURE_DIRECTIONS.md`.

## Current Model

- `big-pickle` (free) via OpenCode Zen, OpenAI-compatible adapter,
  `max_completion_tokens: 4096`, auth via OpenCode's `opencode` credential.
  Unchanged.

## Operational Caveats

- Ensure only one Jimbo instance. If restarting, kill the old process first
  (see `docs/OPERATIONS.md`); `setsid` forks so the recorded `$!` may be the
  wrapper — re-check with `ps`.
- Prompt edits take effect immediately (the prompt is rebuilt per message);
  only code that matters at startup warrants a `startup_change_summary` bump.
- Only stage intentional changes. `*.key`, `rconpw`, `groq-api-key.txt`,
  `jimbo.log`, `jimbo.pid`, `jimbo_says.log`, `last_*.txt`,
  `known_players.txt`, `restart_server.py`, and `new_game.py` remain
  ignored/untracked.
- `restart_server.py` / `new_game.py` are gitignored on purpose: they are
  machine-local operator scripts. If they are later generalized, move reusable
  logic into the repo and keep the local wrappers ignored.
- The old repository (`/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints`)
  used the deprecated `mcrcon` library; do not import its RCON code.
- `LuaSpacePlatform.get_imports()`/`get_requesting()` are gone in 2.1.12; use
  `platform.hub.get_logistic_sections()` for platform requests. See
  `docs/RCON_NOTES.md`.

## Natural Next Action

- Run `restart_server.py` (and, with explicit user confirmation, `new_game.py`)
  to validate them against the live server. Otherwise wait for the user's next
  request. The handoff commit below should be pushed only when the user asks.
