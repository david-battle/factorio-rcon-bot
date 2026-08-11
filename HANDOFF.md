# Handoff

## Verified State

- Branch: `main`; local commits only (the user pushes manually).
- **Jimbo is NOT running.** `jimbo.pid` is stale; no `jimbo.py` process is alive.
  The user intends to leave Jimbo down until they need to test something. Factorio
  is up: RCON answers on `127.0.0.1:27015` and `/version` reports `2.1.14`.
- Jimbo's configured profile is still `free-models-router` (OpenRouter
  `openrouter/free` via `https://openrouter.ai/api/v1`, reading
  `openrouter.key`; never read or print a key). Nothing in `jimbo.py` changed
  this session.
- The backup loop (`backup_loop.py`) is stopped; no process is alive. Its
  handoff (commit `ba1c957`) is already committed.

## Completed Work

### RCON/Lua 2.1.14 learnings (this session, doc-only)

- `docs/RCON_NOTES.md`: added 2.1.14 API drift notes:
  - Player personal logistics requests moved to
    `player.character.get_logistic_sections()`; the old
    `player.get_character_logistic_requests()` /
    `player.get_logistic_requests()` / `player.logistic_requests` APIs are gone.
    `pairs(game.players)` includes offline players, unlike `game.get_player`.
  - Requester-chest filter slot `value` is now a table, not the bare string seen
    on 2.1.12; probe `type(f.value)` first. `LuaInventory.get_item_count(name)`
    rejects the name argument on 2.1.14 — sum `inv.get_contents()` instead.
  - New "Who Is Requesting Item X?" recipe: check personal logistics sections
    first, and do not scan every entity on a surface (that hung the live server
    for over a minute); target specific entity types instead.

## Validation

- `git diff --check` clean.
- No tests run: doc-only change, no Python or behavior touched. (The previous
  session ran `python -m pytest test_jimbo.py -q`: 127 passed; nothing in that
  area changed since.)

## Remaining Work

- Restart Jimbo when the user asks; it is intentionally down and stays down
  until they need to test something. Follow `docs/OPERATIONS.md`; ensure the
  stale `jimbo.pid` process is gone before relaunching.
- The prior handoff's "re-verify 2.1.14-sensitive RCON/Lua API facts" item is
  partially addressed by the new RCON_NOTES entries; keep verifying live before
  relying on them.

## Operational Caveats

- Only stage intentional changes. `*.key`, `rconpw`, `jimbo.log`, `jimbo.pid`,
  `jimbo_says.log`, `backup_loop.*`, `last_*.txt`, `known_players.txt`,
  `restart_server.py`, `new_game.py` remain ignored/untracked (machine-local
  operator data).

## Natural Next Action

- Leave Jimbo down. When the user next wants a live test, restart it per
  `docs/OPERATIONS.md`, then review and push the handoff commit.
