# Handoff

## Verified State

- Branch: `main`; local commits only (the user pushes manually).
- **Jimbo is running** under pid `351221` (see `jimbo.pid`), started 2026-08-03
  10:09, verified alive (single instance). The launcher via `setsid` forks, so
  re-confirm the recorded PID with `ps` from a fresh session.
- **Jimbo runs on `big-pickle`** via OpenCode Zen (OpenAI-compatible,
  `https://opencode.ai/zen/v1`, `auth_provider=opencode` reading
  `~/.local/share/opencode/auth.json`; never read or print a token),
  `max_completion_tokens: 4096`. Big Pickle is free; reasoning stays in
  `usage.reasoning_tokens` and does not leak into `message.content` (verified),
  so no reasoning-exclusion extra body is needed.
- `last_startup_summary.txt` matches the current `startup_change_summary`
  ("I can now read equipment power and buffer values straight from the
  server..."), so the running process already announced the latest change and no
  further `STARTUP_ANNOUNCEMENTS.md` entry is needed for another restart of this
  same code.
- This session's code changes are **uncommitted** (jimbo.py, test_jimbo.py,
  STARTUP_ANNOUNCEMENTS.md, docs/OPERATIONS.md, docs/RCON_NOTES.md); the last
  commits are `be69ab3` and `f9b6e30`.

## Completed Work

### Provider switch to Big Pickle via OpenCode Zen

- New `big-pickle` profile in `jimbo.py` (top-level config block) and
  `ai_profile_name = "big-pickle"`. Same Zen endpoint as `deepseek`, which stays
  defined.
- `docs/OPERATIONS.md`: updated profile table, current-profile paragraph
  (reasoning stays in `usage.reasoning_tokens`, 4096-token cap, no
  `reasoning.exclude` needed unlike OpenRouter Nemotron), and provider history.
- Tests assert the new profile's config and adapter wiring; live-verified a Zen
  call before restarting.

### Prototype lookup improvements (equipment / buffers)

Motivated by Jimbo's guessed exoskeleton buffer (~20 MJ) being wrong. Live
fact-finding (2.1.12 + space-age mods):

- Equipment lives under `prototypes.equipment`, not `prototypes.entity`; names
  are `personal-roboport-equipment`, `personal-roboport-mk2-equipment`,
  `exoskeleton-equipment`. Blind guessed keys fail with "attempt to index field
  ... (a nil value)".
- Buffer = `p.energy_source.buffer_capacity` in joules: personal roboport =
  35,000,000 (35 MJ), exoskeleton = 0 (no internal buffer; draws from armor
  grid). Re-verified twice at the user's request.
- 2.1.12 Lua wrappers do NOT expose `energy_consumption`, `movement_bonus`,
  `consumption`, or `input_flow_limit` on equipment/energy-source prototypes
  (`LuaEquipmentPrototype doesn't contain key X`); `pairs()` also fails on
  them, so field reads must be `pcall`-wrapped.

Changes:

- Hardened the classifier prompt (jimbo.py ~1913-1942): internal names vs
  player-facing names, enumerate with `pairs()` + `:find()` when uncertain,
  buffer semantics, `pcall` per field, never invent unread values.
- Added 2 tests (`test_classifier_knows_equipment_prototypes_and_enumeration`,
  `test_classifier_knows_equipment_buffer_reading_and_pcall`).
- `docs/RCON_NOTES.md`: added equipment facts and the unexposed-key gotchas.
- Updated `startup_change_summary` and appended three `STARTUP_ANNOUNCEMENTS.md`
  entries (2026-08-03 ~08:?? model switch, ~09:?? lookups, ~10:?? equipment
  values).
- Verified live: a question about the exoskeleton buffer produced a
  `/silent-command` pcall query returning `0.0 MJ`, and Jimbo's reply cited the
  live value instead of guessing.

## Validation

- `python -m py_compile jimbo.py` clean; `git diff --check` clean.
- `python -m unittest test_jimbo` — 123 tests, all passing (5 added this
  session: 3 profile-config assertions + 2 equipment-prompt tests).
- Not run: `test_ollama.py` (per operations guidance, avoid while the Factorio
  client uses the GPU).

## Remaining Work

- None pending. The exoskeleton fix is live; if a future question needs a
  different equipment prototype, the enumeration guidance should cover it. The
  OpenRouter 429 rate-limit issue from the prior handoff is moot (provider is
  now Big Pickle via Zen, free).
- Residual limitation (from prior handoff, unchanged): `TAG` cannot filter
  assembling machines by current recipe. See `docs/FUTURE_DIRECTIONS.md`.

## Current Model

- `big-pickle` (free) via OpenCode Zen, OpenAI-compatible adapter,
  `max_completion_tokens: 4096`, auth via OpenCode's `opencode` credential.
  Changed this session.

## Operational Caveats

- Ensure only one Jimbo instance. If restarting, kill the old process first
  (see `docs/OPERATIONS.md`); `setsid` forks so the recorded `$!` may be the
  wrapper — re-check with `ps`.
- Only stage intentional changes. `*.key`, `rconpw`, `groq-api-key.txt`,
  `jimbo.log`, `jimbo.pid`, `jimbo_says.log`, `last_*.txt`, and
  `known_players.txt` remain ignored/untracked.
- The old repository (`/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints`)
  used the deprecated `mcrcon` library; do not import its RCON code.
- 2026-08-01 learnings apply: chat delivery uses
  `/silent-command game.forces.player.print(...)` with
  `sound_path="item-move/logistic-robot"` and `ensure_ascii=False` (Factorio's
  Lua 5.1 rejects `\uXXXX` escapes). See `docs/RCON_NOTES.md`.

## Natural Next Action

- Wait for the user's next request. The handoff commit below should be pushed
  only when the user asks.
