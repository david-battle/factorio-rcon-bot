# Handoff

## Current State

- Branch: `main`; this context started from `8fe4daa`.
- Jimbo is running as PID `186852` with the `openai/gpt-5.4-mini` profile and
  the research-level fix active.
- The latest reviewed server chat timestamp is `2026-07-29 06:20:00`.
- `AGENTS.md` is authoritative. Use `OPERATIONS.md` for runtime procedures and
  read `FUTURE_DIRECTIONS.md` before feature work based on live experiments.

## Completed Work

- Diagnosed a live situational-awareness failure after Jimbo announced Scrap
  Recycling Productivity at 77.62% without its level, then could not confirm the
  player's reference to level 3.
- Confirmed that the follow-up was classified as `NONE` and reused the incomplete
  spontaneous dialogue fact rather than issuing a fresh RCON query.
- Fixed research snapshot formatting to identify repeatable technologies through
  `LuaTechnologyPrototype.max_level` and append the actual `LuaTechnology.level`,
  including repeatables whose internal names have no numeric suffix.
- Updated reply guidance and deterministic coverage for
  `scrap-recycling-productivity` at level 3.
- Updated `startup_change_summary`, restarted Jimbo, and verified the player-facing
  startup announcement was delivered.

## Validation

- `python -m py_compile jimbo.py test_jimbo.py` passed.
- `python -m unittest -v test_jimbo` passed all 36 deterministic tests.
- `git diff --check` passed.
- The live research query returned `Current: scrap recycling productivity 3` at
  `77.62%`, with the same level shown in the queue.
- Broad unittest discovery was not used as validation because it imports the live
  `test_ollama.py` script, which hit the documented GPU out-of-memory condition.

## Remaining Work

- No implementation is partially complete and no blocker remains.
- The natural next action is to monitor the next research-related follow-up in
  live chat; no further change is needed unless another concrete awareness failure
  appears.

## Operational Caveats

- Do not restart Jimbo, Factorio, or another service merely to resume work.
- Do not run live `test_ollama.py` while the Factorio client is using the GPU.
- Credentials, runtime logs, PID/state files, player data, caches, local tools,
  and `last_chat_review.txt` remain ignored and must not be committed.
- Direct assistant RCON queries in this context were read-only verification, not
  actions or capabilities exercised autonomously by Jimbo.
