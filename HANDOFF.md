# Handoff

## Verified State

- Branch: `main`; local commits only (the user pushes manually).
- **Jimbo is running** under pid `353102` (see `jimbo.pid`), verified alive.
  The launcher via `setsid` forks, so re-confirm the recorded PID with `ps`
  from a fresh session.
- **Jimbo runs on `big-pickle`** via OpenCode Zen (OpenAI-compatible,
  `https://opencode.ai/zen/v1`, `auth_provider=opencode` reading
  `~/.local/share/opencode/auth.json`; never read or print a token),
  `max_completion_tokens: 4096`.
- `last_startup_summary.txt` matches the current `startup_change_summary`
  ("I now remember about 40 minutes of recent chat instead of 15..."), so no
  further `STARTUP_ANNOUNCEMENTS.md` entry is needed.
- All changes to date are committed; the tracked worktree is clean (the
  session's `docs/RCON_NOTES.md` update is captured in the handoff commit).
  Pending the user's manual push.

## Completed Work

### Platform-to-platform logistics diagnosis (live RCON + notes, this session)

The player's platforms `[planet=nauvis] Station` (provider) and `Tiny`
(requester) are both in Nauvis orbit. Tiny requests 2 chemical plants with
`request_from=platforms`, and Station holds 9 chemical plants in hub storage,
yet nothing ships ("not on the way"). Root cause: **Station has its own active
import request for chemical plants (`min=10`)**; a provider reserves its stock
for its own request and will not dispatch that item to other platforms. The
user-side fix is to remove/disable Station's chemical-plant import row.

- Diagnosis used a new API: on 2.1.12 `LuaSpacePlatform.get_imports()` and
  `get_requesting()` no longer exist; platform requests live on
  `platform.hub.get_logistic_sections().sections` (filters are plain tables
  with `value`/`min`/`max`/`import_from`/`request_from`).
- Recorded all new RCON/Lua learnings in `docs/RCON_NOTES.md` (new "Space
  Platform Requests (2.1.12)" section; `LuaInventory.get_contents()` return
  shape; no `defines.inventory.cargo_bay`; `game.active_mods` gone; hub
  "provide" toggle has no API). No Jimbo code was changed.

## Validation

- Doc-only change; `git diff --check` clean. No tests rerun (nothing
  behavior-changing). Not run: `test_ollama.py` (per operations guidance,
  avoid while the Factorio client uses the GPU).
- RCON facts above were verified live against 2.1.12 and cross-checked with
  the 2.1.12 API docs.

## Remaining Work

- None pending in code. The in-game fix (removing Station's chemical-plant
  import request) is a manual player action; the platform reserve-on-own-request
  gotcha is documented in `docs/RCON_NOTES.md`.
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
- Only stage intentional changes. `*.key`, `rconpw`, `groq-api-key.txt`,
  `jimbo.log`, `jimbo.pid`, `jimbo_says.log`, `last_*.txt`, and
  `known_players.txt` remain ignored/untracked.
- The old repository (`/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints`)
  used the deprecated `mcrcon` library; do not import its RCON code.
- `LuaSpacePlatform.get_imports()`/`get_requesting()` are gone in 2.1.12; use
  `platform.hub.get_logistic_sections()` for platform requests. See
  `docs/RCON_NOTES.md`.

## Natural Next Action

- Wait for the user's next request. The handoff commit below should be pushed
  only when the user asks.
