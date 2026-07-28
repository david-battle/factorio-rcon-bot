# Handoff

## Current State

- Branch: `main`; it was already one commit ahead of `origin/main` before the
  handoff commit.
- Jimbo remains the deliberately simple server-log, AI decision/reply, and RCON
  bot centered in `jimbo.py`; no Jimbo code changed in this context.
- The active `openai` profile remains `openai/gpt-5.4-mini` through OpenCode.
  DeepSeek, optional Groq, and local Ollama remain manually selectable; there is
  no automatic fallback and Mistral is not configured.
- Owner and AI configuration remain centralized at the top of `jimbo.py`.

## Completed Work

- `OPERATIONS.md` now records concurrent RCON authentication, exact 32 x 32
  chunk alignment, safe settings-preserving blueprint deployment, compact
  production-cell construction, module-request substitution, power bridging,
  and logistic reserve-drain diagnosis. It also defines "old repository" as
  `/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints`.
- `FUTURE_DIRECTIONS.md` records the recommended minimal path toward bounded
  one-chunk blueprint design: a strict offline codec and validator first, without
  importing the old full bot or design-specific generators.
- `.opencode/command/handoff.md` now requires saving recent reusable learnings in
  the appropriate Markdown file before preparing `HANDOFF.md`.
- `SYSTEM_ADMIN.md` records that `jq` 1.8.1 is installed and verified in WSL.
- Live work configured seven compact equipment production cells and deployed the
  old QUP crusher blueprint into the Nauvis chunk bounded by `(32,96)` and
  `(64,128)`. The QUP received an explicit external copper bridge and 32
  normal-quality Quality Module 2s because Quality Module 3s were unavailable.
- An older quality-storage bank was draining the QUP reserve chests. The user
  limited the Normal crusher chest; the Uncommon, Rare, Epic, and Legendary
  crusher buffer chests were then limited to one usable slot each. Their large
  requests remain configured but cannot continue deliveries after available
  space fills.

## Validation

- No runtime code changed, so no startup summary or Jimbo restart is required for
  this commit.
- `python -m py_compile jimbo.py test_jimbo.py` passed.
- `python -m unittest -v test_jimbo` passed all 25 deterministic tests.
- `git diff --check` passed.
- A bounded live read-only check confirmed Factorio 2.1.12, all eight QUP
  assemblers plus its recycler powered, all 32 Quality Module 2s installed, the
  crusher chest bars at `20,2,2,2,2`, and all seven equipment recipes retained.
- Do not run live `test_ollama.py` while the Factorio client is using the GPU.

## Remaining Work

- QUP is a historical Factorio 2.1.11 beta now running on 2.1.12. Monitor its
  recycling and quality routing before treating it as a proven current design.
- Blueprint design remains a documented future direction, not a Jimbo feature.
  If explicitly requested, begin with the small offline codec/validator described
  in `FUTURE_DIRECTIONS.md`, not the old full-bot architecture.
- GPS-only engagement can still produce ungrounded movement claims. Grounded GPS
  inspection remains the most natural next Jimbo feature.

## Operational Caveats

- Do not restart Jimbo, Factorio, or another service merely to resume work.
- Credentials, runtime logs, PID/state files, player data, caches, and chat review
  state remain ignored and must not be committed.
- Read `OPERATIONS.md` before RCON, blueprint, production-cell, provider, process,
  or recovery work; its procedures are authoritative over the old repository.
