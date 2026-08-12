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

### RCON/Lua: deconstruction API semantics (this session, doc-only)

- `docs/RCON_NOTES.md` (Verified Runtime Facts): `order_deconstruction(force)`
  returns `true` when newly marked, `false` when already marked/not
  deconstructable — not an error string; `to_be_deconstructed` is a **method**
  on 2.1.14. Learned live while marking all 16,005 lamps on Nauvis for
  deconstruction (bots removed 2,861 immediately; the remaining 13,144 are all
  marked). Live RCON action only; no repo impact.

### RCON/Lua: prominent `pcall` first rule (prior session, doc-only)

- `docs/RCON_NOTES.md`: added a "FIRST RULE" callout near the top of the file:
  probe entity fields with `pcall` because Factorio raises instead of returning
  nil on the wrong entity kind. Learned live this session when `e.ghost_name` on
  a non-ghost aborted a requester scan (`/silent-command` error "Entity is not
  ghost").
- Live RCON session this handoff (not committed, no repo impact): located the
  only Aquilo requester of `quantum-processor` (requester-chest `#11056398` at
  (19.5,-8.5), min=600) and tagged it in-game with a "Jimbo ping" chart tag.

### RCON/Lua 2.1.14 learnings (prior session, doc-only)

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
- The chart tag left at Aquilo (19.5,-8.5) is a map marker only; nothing to
  remove or commit.

## Operational Caveats

- Only stage intentional changes. `*.key`, `rconpw`, `jimbo.log`, `jimbo.pid`,
  `jimbo_says.log`, `backup_loop.*`, `last_*.txt`, `known_players.txt`,
  `restart_server.py`, `new_game.py` remain ignored/untracked (machine-local
  operator data).

## Natural Next Action

- Leave Jimbo down. When the user next wants a live test, restart it per
  `docs/OPERATIONS.md`, then review and push the handoff commit.
