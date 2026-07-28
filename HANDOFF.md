# Handoff

## Current State

- Branch: `main`; it matched `origin/main` before the handoff commit.
- Jimbo remains a simple server-log, AI decision/reply, and RCON bot centered in
  `jimbo.py` with deterministic coverage in `test_jimbo.py`.
- The active `openai` profile uses `openai/gpt-5.4-mini` through OpenCode.
  DeepSeek, optional Groq, and local Ollama profiles remain manually selectable;
  there is no automatic fallback and Mistral is not configured.
- Owner, model, provider, endpoint, and identity configuration remains
  centralized at the top of `jimbo.py`.

## Completed Work

- No Jimbo code changed in this context, so no restart summary was needed.
- `OPERATIONS.md` now records the verified Power Armor MK2 recipe requests and
  makes validated power extension standard practice for compact production cells
  that fall outside existing electric coverage.
- The power-extension procedure requires collision and construction-network
  checks, quality-aware supply coverage, explicit copper wiring to a live pole,
  connection verification, and rollback of the new pole with the cell ghosts.

## Validation

- `python -m py_compile jimbo.py test_jimbo.py` passed.
- `python -m unittest -v test_jimbo` passed all 25 deterministic tests.
- `git diff --check` passed.
- The live `test_ollama.py` smoke was not run because it can load the 28 GB local
  model and conflict with the Factorio game client using the GPU.

## Remaining Work

- GPS-only engagement such as `Jimbo [gps=...]` can still produce ungrounded
  movement claims. The natural next feature is grounded GPS inspection, using
  the verified techniques referenced in `FUTURE_DIRECTIONS.md` and
  `OPERATIONS.md`.
- The current production-cell guidance is operational documentation, not an
  automated Jimbo feature. Do not add generalized building automation without a
  new explicit request.

## Operational Caveats

- Do not restart Jimbo, Factorio, or another service merely to resume work.
- Credentials, runtime logs, PID/state files, player data, caches, and the chat
  review marker remain ignored and must not be committed.
- Read `OPERATIONS.md` for provider setup, process management, testing, save
  recovery, and detailed verified RCON procedures.
