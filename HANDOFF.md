# Handoff

## Verified State

- Branch `main`; local commits only (the user pushes manually).
- **Jimbo is RUNNING** (PID from `jimbo.pid`, `python -u jimbo.py`, gitignored
  `jimbo.log`), last restarted 2026-08-23 22:36 with all of this session's
  changes live. Leave it running unless the user says otherwise.
- `ai_profile_name = "deepseek"` (jimbo.py, top config block) — paid
  `deepseek-v4-flash` via OpenCode Zen, reading the `opencode` credential from
  `~/.local/share/opencode/auth.json`; never read or print a token. The
  `server_owner` / `ai_profiles` values stayed in that single block per the
  always-preserve rule.
- Factorio is up: RCON answers on `127.0.0.1:27015`, version `2.1.14`. Server
  log at `/mnt/d/factorio-server/server-console.log`.

## Completed Work (2026-08-23 failure-mode session)

`FIX_PLAN.md` is new: it records the day's chat-debugging items and their
dispositions. Items 1, 2, 4, and 5 shipped the same day and were deleted from
the plan per its merge rule; item 3 is a multi-step roadmap; item 6 is
deferred.

1. **Lookup slash-prefix normalization.** `compose_lookup_command` now wraps
   bare-Lua model responses with `/silent-command `, applies
   `forbidden_lua_reason` after normalization, and logs raw responses instead
   of discarding them (previously "model returned no command" failures hid
   the cause).
2. **Ghost idiom in the scripting reference.** `generate_lua_reference.py`
   RULES now teach ghost identification (`e.type == "entity-ghost"`,
   `"tile-ghost"`; no `e.ghost` field; `ghost_type`/`ghost_name` raise on
   non-ghosts). `lua_essentials.txt` regenerated from the installed 2.1.14
   docs. Verified live: Jimbo deleted his own stray ghosts by type filter.
3. **Classifier calibration.** `_is_recognized_classification` was missing
   `parse_lookup_decision`, so every correct LOOKUP first-answer burned a
   wasted retry (~5 s + one AI call); it is in the recognized set now.
   Unrecognized classifier output is logged verbatim for diagnosis.
4. **Entity removal verb (`REMOVE|surface|entity-type|location`).**
   Owner decisions recorded in `docs/BOT_CONTRACTS.md` ("Entity Removal"): no
   ownership tracking and no engineered guardrails — ghosts are destroyed,
   real entities get `order_deconstruction('player', player)` so bots
   dismantle and items are recovered. Implementation:
   `parse_remove_decision` (`any` type allowed, surface `all` allowed,
   optional location defaulting to view), `remove_entities` single-command
   Lua (64-tile radius constant `remove_area_radius`; resolves `current`,
   named surfaces, and `all`), classifier prompt bullet with an
   intent-fidelity nudge (prefer the specific type the player names over
   `any`), dispatch block, and a terse-counts reply hint. Live-tested:
   40-ghost cleanup answered in one short sentence.
5. **Docs.** New runtime facts in `docs/RCON_NOTES.md`
   (`order_deconstruction` optional player/undo_index params;
   `find_entities_filtered{name=...}` raises on unknown names rather than
   returning empty). `docs/FUTURE_DIRECTIONS.md` direction 12 captures the
   request-time layout-synthesis vision; the active step-by-step roadmap is
   `FIX_PLAN.md` item 3 Step 1 (parameterized layouts; belt-fed cell modeled
   on the owner's hand-built parallel-belt example near nauvis [gps=13,7]).

## Validation

- `python -m py_compile jimbo.py test_jimbo.py generate_lua_reference.py` OK.
- `python -m pytest test_jimbo.py` — 162 passed, 43 subtests passed.
- `git diff --check` clean.
- Live RCON checks before each restart: empty-area zero counts, missing-
  surface error, offline-player guard, `current`-surface resolution, `any`
  unfiltered search.
- Did NOT run `test_ollama.py` (the Factorio client is using the GPU).

## Operational Caveats

- Only stage intentional changes. `*.key`, `rconpw`, `jimbo.log`, `jimbo.pid`,
  `jimbo_says.log`, `jimbo_commands.log`, `backup_loop.*`, `last_*.txt`,
  `known_players.txt`, `restart_server.py`, `new_game.py` remain
  ignored/untracked (machine-local operator data).
- Do not restart or stop Jimbo/Factorio as part of a handoff unless the user
  asks; leave the current running process alone.
- The old repository at
  `/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints` is reference
  material only (owner's explicit instruction): mine it for layout geometry
  and generate-validate-test patterns; never treat its content as
  authoritative or import its framework.

## Natural Next Action

- Start `FIX_PLAN.md` item 3 Step 1: lift cell layouts into parameterized
  Python entity tables (rotation, lanes-per-side, belt-vs-chest I/O knobs)
  and add the belt-fed shape, shipping the reply-prompt honesty rule together
  with it (see also `FUTURE_DIRECTIONS` direction 12). Then push this handoff
  commit (user pushes manually).
