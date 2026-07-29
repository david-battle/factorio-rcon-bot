# Handoff

## Current State

- Branch: `main`; this context started from `781e65b`.
- Jimbo is running as PID `169933` with the `openai/gpt-5.4-mini` profile. No
  code changed in this context, and no process was restarted.
- The latest reviewed server chat timestamp is `2026-07-28 20:48:29`.
- `AGENTS.md` is authoritative. Use `OPERATIONS.md` for current runtime and
  operator procedures, and read `FUTURE_DIRECTIONS.md` before feature work based
  on live experiments.

## Completed Work

- Reorganized documentation so planned Jimbo capabilities and their tested live
  implementation findings are in `FUTURE_DIRECTIONS.md`, not `OPERATIONS.md`.
- Moved blueprint deployment, ghost inspection/cloning, logistic machine
  conditions, production diagnosis, logistic-group mutation, production-cell
  construction, and research-control findings.
- Added grounded production diagnosis and bounded logistic controls as an
  explicit future direction.
- Kept `OPERATIONS.md` focused on current Jimbo behavior, RCON access, provider
  operation, process management, testing, saves, and runtime pitfalls.
- Added the required `FUTURE_DIRECTIONS.md` reference to `AGENTS.md` so future
  feature contexts load the experimental evidence before implementation.

## Live Experiment Context

- The development assistant directly configured five Fulgora holmium consumers
  to run only above 1,200 available normal holmium plates and independently
  verified the conditions. A player later removed that setup; do not assume those
  conditions remain active.
- Nauvis diagnosis found processing units heavily buffered in requester chests
  and idle consumers, while utility science was processing-unit-starved. Tracing
  upstream found advanced-circuit and local oil throughput constraints. The
  player subsequently added speed modules to all pumpjacks.
- These were assistant RCON investigations/actions, sometimes formatted with
  `Jimbo says ` at the user's request. They were not capabilities exercised by
  the running Jimbo process, and live factory values are transient.

## Validation

- `python -m py_compile jimbo.py test_jimbo.py` passed.
- `python -m unittest -v test_jimbo` passed all 36 deterministic tests.
- `git diff --check` passed.

## Remaining Work

- No implementation is partially complete. The natural next action is to choose
  one direction from `FUTURE_DIRECTIONS.md` and design the smallest grounded,
  deterministic feature before editing `jimbo.py`.
- If production diagnosis is selected, begin with a bounded read-only query and
  deterministic fixture rather than exposing arbitrary recursive Lua or mutation.

## Operational Caveats

- Do not restart Jimbo, Factorio, or another service merely to resume work.
- Do not replay mutating RCON commands after an uncertain disconnect.
- Rediscover live entities before mutation; unit numbers and factory state can
  change when players rebuild or alter the setup.
- Credentials, runtime logs, PID/state files, player data, caches, local tools,
  and `last_chat_review.txt` remain ignored and must not be committed.
