# Handoff

## Architecture & Running State

- Branch: `main`; this context started from `ffd7fb5`.
- Jimbo is running as PID `186852` with the `openai/gpt-5.4-mini` profile and
  the research-level fix deployed. The production cell code is **not yet active**
  — the classifier prompt and main loop dispatch are unwired (Step 3 pending).
- `AGENTS.md` is authoritative. Read `OPERATIONS.md` for runtime procedures and
  `FUTURE_DIRECTIONS.md` before feature work based on live experiments.

## Completed Work (this session)

- **Alert-awareness planning** (`ALERT_AWARENESS.md`): Designed a feature so
  Jimbo reads `game.forces.player.alerts` and includes active alert state in
  spontaneous commentary and reply prompts. On hold pending production cell
  completion.
- **Production cell placement — Steps 1 & 2** (see `PROD_CELL_PLACE.md`):
  - Step 1: `parse_produce_decision()` validates `PRODUCE|surface|item|hint`
    lines and returns parsed fields. `place_production_cell()` runs Phase 1 Lua
    (location search with power + logistic preflight) and returns `ANCHOR` or
    error.
  - Step 2: Extended `place_production_cell()` with Phase 2 Lua that ghost-places
    a building (entity resolved from recipe category), requester chest, provider
    chest, two inserters, and a medium electric pole. Sets requester filters from
    recipe ingredients, verifies construction registration, and rolls back all
    ghosts on any failure. Phase 2 uses `retry=False` — it never replays a
    mutation on reconnect.
- **Entity resolution**: Phase 1 now maps recipe categories (`crafting`,
  `electronics`, `metallurgy`, etc.) to Space Age building prototypes via a Lua
  table, falling back to the product name if it is itself a placeable entity.
- Updated `startup_change_summary` for the production cell capability.

## Validation

- `python -m py_compile jimbo.py test_jimbo.py` passes.
- `python -m unittest test_jimbo` — all 54 deterministic tests pass.
- `git diff --check` passes.

## Remaining Work

### Production Cell (Steps 3–6 in PROD_CELL_PLACE.md)

| Step | Description | Status |
|------|-------------|--------|
| 1 | `parse_produce_decision()`, Phase 1 location search | done |
| 2 | Phase 2 ghost placement + verification + rollback | done |
| 3 | **Classifier prompt, dispatch block, reply hint** | next |
| 4 | Power extension subplan | pending |
| 5 | Location spiral for player-free hints | pending |
| 6 | Dynamic prototype dimension lookup | pending |

Step 3 wires `PRODUCE|...` into `build_classification_prompt()`, adds the
classifier `elif`, runs `place_production_cell()` in the dispatch block, and
injects the produce hint into `build_reply_prompt()`.

### Alert Awareness (on hold)

See `ALERT_AWARENESS.md` for the full design. No code has been written yet.

## Operational Caveats

- Do not restart Jimbo, Factorio, or another service merely to resume work.
- Do not run live `test_ollama.py` while the Factorio client is using the GPU.
- Credentials, runtime logs, PID/state files, player data, caches, local tools,
  and `last_chat_review.txt` remain ignored and must not be committed.
- After this code is deployed (Jimbo restart), test `PRODUCE|...` by sending a
  chat with a GPS ping on a surface with power + logistic coverage.

## Natural Next Action

Implement **Step 3** of `PROD_CELL_PLACE.md`: add `PRODUCE|` to the classifier
prompt, its `elif` branch, the dispatch block calling
`place_production_cell()`, and the produce hint in `build_reply_prompt()`.
