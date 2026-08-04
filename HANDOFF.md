# Handoff

## Verified State

- Branch: `main`; local commits only (the user pushes manually).
- **Jimbo is running** under pid `363477` (see `jimbo.pid`), verified alive.
  The launcher via `setsid` forks, so re-confirm the recorded PID with `ps`
  from a fresh session.
- **Jimbo runs on `big-pickle`** via OpenCode Zen (OpenAI-compatible,
  `https://opencode.ai/zen/v1`, `auth_provider=opencode` reading
  `~/.local/share/opencode/auth.json`; never read or print a token),
  `max_completion_tokens: 4096`.
- `startup_change_summary` was updated this session to:
  "I now read location links properly: when you share one from another planet,
  I use the planet it names instead of assuming it's where you're standing."
  This differs from `last_startup_summary.txt`, so a new entry was appended to
  `STARTUP_ANNOUNCEMENTS.md` under 2026-08-04 and the announcement was
  broadcast on restart (observed in `jimbo_says.log` at 06:50:47).

## Completed Work

### GPS‑link location awareness (player‑visible change)

- Updated prompt classifiers and reply logic to use the planet embedded in a
  `[gps=x,y,surface]` link instead of the player's current surface; bare
  `[gps=x,y]` links have unknown planet and must be resolved from context.
- Updated `startup_change_summary` and `STARTUP_ANNOUNCEMENTS.md` accordingly.

### Startup announcement procedure rewrite (so future prompt/behavior changes are noted)

- AGENTS.md: rule now reads "If a change will alter player‑visible behavior after
  restart — code or prompt — update `startup_change_summary`…"
- docs/HANDOFF_PROCEDURE.md step 6: same criterion ("code or prompt").
- docs/BOT_CONTRACTS.md Startup Announcements: added "Update the summary for
  every change that will alter player‑visible behavior after restart — code or
  prompt — not only code."
- HANDOFF.md caveat: replaced "only code that matters at startup warrants a
  bump" with "Prompt edits that change player‑visible behavior warrant a
  `startup_change_summary` bump just like code changes…"

### Durable documentation updates

- docs/RCON_NOTES.md: added electric‑network API quirks and Map Pings note
  (game omits surface when it matches the player's current surface).

## Validation

- `python -m py_compile jimbo.py` clean; `git diff --check` clean.
- `python -m pytest test_jimbo.py -q`: **127 passed, 43 subtests passed**.
- Not run: `test_ollama.py` (per operations guidance, avoid while the Factorio
  client uses the GPU).

## Remaining Work

- No pending code changes from this session. The tracked worktree is clean after
  this commit; the user will push manually.

## Operational Caveats

- **server‑console.log** LastWriteTime was 06:38:44 while the server is alive
  (autosaves at 06:41/06:51, RCON connected, announcement at 06:50 broadcast).
  Verify it is still receiving writes; if stale, Jimbo will not see new chat.
- Ensure only one Jimbo instance. If restarting, kill the old process first
  (see `docs/OPERATIONS.md`); `setsid` forks so the recorded `$!` may be the
  wrapper — re‑check with `ps`.
- Prompt edits that change player‑visible behavior warrant a
  `startup_change_summary` bump just like code changes (see `AGENTS.md`).
- Only stage intentional changes. `*.key`, `rconpw`, `groq-api-key.txt`,
  `jimbo.log`, `jimbo.pid`, `jimbo_says.log`, `last_*.txt`,
  `known_players.txt`, `restart_server.py`, `new_game.py` remain
  ignored/untracked.
- `restart_server.py` / `new_game.py` are gitignored on purpose: they are
  machine‑local operator scripts.

## Natural Next Action

- Review and push the handoff commit when ready. Otherwise wait for the user's
  next request.