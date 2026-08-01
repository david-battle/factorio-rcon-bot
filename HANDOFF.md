# Handoff

## Verified State

- Branch: `main`; local commits only (the user pushes manually).
- Jimbo is running under a fresh pid from this session's restart (check
  `jimbo.pid`; the old process was killed first per `docs/OPERATIONS.md`).
  The Factorio server was up; RCON returned `/version` 2.1.12.
- The `deepseek` profile (`deepseek-v4-flash-free` via the OpenCode AI API) is used.
- `last_startup_summary.txt` matches the current `startup_change_summary` (the
  game-alerts spontaneous-comment note was announced on restart).
- See `AGENTS.md` and `docs/OPERATIONS.md` for architecture and running procedures.
  `docs/BOT_CONTRACTS.md` holds behavioral contracts.

## Completed Work

- **Alert awareness in spontaneous comments implemented.** Jimbo now fetches a
  grouped game-alerts snapshot (`surface|type:count`) from
  `game.forces.player.alerts` via `get_alerts_snapshot()` and includes it in the
  scheduled spontaneous prompt. `prepare_alerts_for_prompt()` debounces
  `no_platform_storage` until it persists across two snapshots (it can fire
  briefly while orbital requests are allocated). Active alerts can break the
  already-announced research-stall silence; an empty snapshot says explicitly
  there are no active alerts. Alert-grounded replies record the exact snapshot
  in dialogue via `reply_uses_alerts_context()`. Previous alert keys are tracked
  in `spontaneous_state["alerts_prev_keys"]` and reset on offline/forget.
- Every prompt/summary change has a matching entry in `STARTUP_ANNOUNCEMENTS.md`
  under 2026-08-01 and was announced on restart.
- `docs/FUTURE_DIRECTIONS.md` marks the spontaneous portion implemented and the
  `ALERTS|surface` classifier dispatch + alert-related direct replies as still
  unimplemented.

## Validation

- `python -m py_compile jimbo.py` clean; `git diff --check` clean.
- `python -m unittest test_jimbo` ran 115 tests, all passing. 7 new tests cover
  the alerts snapshot, `no_platform_storage` debounce, immediate real alerts,
  prompt inclusion, dialogue context recording, and stalled-silence breaking.
- Not run this session: live RCON alert probing. The snapshot function is
  deterministic-tested but has not been observed against a live alerting server.

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
