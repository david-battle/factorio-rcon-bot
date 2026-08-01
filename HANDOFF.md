# Handoff

## Verified State

- Branch: `main`; local commits only (the user pushes manually).
- Jimbo is running (check `jimbo.pid`; a fresh process was started each restart
  this session). The Factorio server was up; RCON probes succeeded.
- The `deepseek` profile (`deepseek-v4-flash-free` via the OpenCode AI API) is used.
- `last_startup_summary.txt` matches the current `startup_change_summary` (the
  Chinese/Vulcanus translation note).
- See `AGENTS.md` and `docs/OPERATIONS.md` for architecture and running procedures.
  `docs/BOT_CONTRACTS.md` holds behavioral contracts.

## Completed Work

- **Reactor power math fixed and verified live.** Jimbo's model-generated Lua
  failed three times: (1) `1e6..' MW'` malformed-number syntax trap, (2) a
  nonexistent `get_energy_source()` method, (3) counting phantom neighbors with
  `find_entity` at a ±1 offset (5x5 reactors return their own bounding box).
  Correct recipe now in the classification prompt: 40 MW per nuclear reactor
  scaled by `1 + neighbours*neighbour_bonus` (bonus=1), counting neighbors
  against the position list at a **±5 tile** offset, and 250 MW per fusion
  reactor. Live probe confirmed the 61-reactor farm is **8,680 MW → 35 fusion
  reactors** (the model's 12,200 MW / 49 was the phantom-neighbor overcount).
- **Translation behavior restored.** The NONE reply hint was rewritten so
  in-chat language tasks (translate, summarize, game knowledge) are answered
  instead of refused, opaque `[special-item=...]` links are explained as
  unreadable, and refusals are limited to unavailable server actions. Added a
  Chinese-slang note: players call Vulcanus 火星 (lit. "Mars").
- **`docs/RCON_NOTES.md`** gained live-verified facts: no `energy_source` /
  `get_energy_source()` on reactor entities or prototypes on 2.1.12
  (`neighbour_bonus` and `burner_prototype` instead; `pairs()` on prototype
  userdata raises), ±5 reactor adjacency probing, and the `1e6..` concatenation
  trap.
- Every prompt/summary change has a matching entry in `STARTUP_ANNOUNCEMENTS.md`
  under 2026-08-01 and was announced on restart.

## Validation

- `python -m py_compile jimbo.py` clean; `git diff --check` clean.
- Live RCON probes: reactor neighbor counting at ±1 vs ±5, WALYY player object
  (offline, character nil), planet list (nauvis/vulcanus/fulgora/gleba/aquilo).
- NOT run: `python -m unittest test_jimbo` (light handoff; no deterministic
  tests added this session).

## Remaining Work

- None pending. Wait for the next request.

## Operational Caveats

- Ensure only one instance of Jimbo is running. If restarting, kill the old
  process first (see `docs/OPERATIONS.md`).
- Only stage intentional changes. `*.key` files, `rconpw`, `groq-api-key.txt`,
  `jimbo.log`, `jimbo.pid`, and state files remain ignored/untracked.
- The old repository (`/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints`)
  used the deprecated `mcrcon` library; do not import its RCON code.

## Natural Next Action

- Wait for the user's next request.
