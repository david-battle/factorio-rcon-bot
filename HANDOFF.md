# Handoff

## Verified State

- Branch: `main`.
- Jimbo is running in the background (`python -u jimbo.py`, PID 311581); single instance.
- The `deepseek` profile (`deepseek-v4-flash-free` via the OpenCode AI API) is currently used.
- `last_startup_summary.txt` matches the current `startup_change_summary`; the map-ping change was announced on the last restart.
- See `AGENTS.md` and `docs/OPERATIONS.md` for architecture and running procedures. `docs/BOT_CONTRACTS.md` holds behavioral contracts.

## Completed Work

- **TOP_DAMAGE map ping fix**: `run_top_damage_command` in `jimbo.py` now appends an exact `[gps=x,y,surface]` to its verified success response. The reply prompt tells Jimbo to include that markup verbatim, and a new deterministic `ensure_gps_ping()` fallback appends a `Requested location: [gps=...]` line when the model omits it. Previously Jimbo claimed to ping the map but only sent plain-text coordinates.
- **Provider switch**: `ai_profile_name` is now `deepseek` (DeepSeek V4 Flash free via the OpenAI-compatible OpenCode API). Added a `nemotron` profile (Nemotron 3 Ultra free via OpenRouter, `openrouter.key`) left configured per the owner; kept in case the owner wants to try it again.
- **Cleanup of abandoned session**: added `*.key` to `.gitignore` (covers `openrouter.key` and the leftover `gemini.key`; no keys deleted). Fixed `test_all_historical_ai_profiles_are_predefined` and `test_ai_profile_selects_its_provider_adapter` for the new profile, updated the provider table and "current profile" text in `docs/OPERATIONS.md`.
- **Tests**: added coverage for the exact-ping response, the reply-hint requirement, and all `ensure_gps_ping` branches.
- `startup_change_summary` and `STARTUP_ANNOUNCEMENTS.md` updated for the map-ping change (21:48 entry).

## Validation

- Ran `python -m unittest test_jimbo`: all 105 tests passed.
- Ran `python -m py_compile` on `jimbo.py` and `test_jimbo.py`; clean.
- Ran `git diff --check`; clean.
- Restarted Jimbo and verified the new startup announcement went out in game. `test_ollama.py` was not run (live, needs the GPU).

## Remaining Work

- None pending from this session. The map-ping fix is live in the running process.

## Operational Caveats

- Ensure only one instance of Jimbo is running. If restarting, kill the old process first (see `docs/OPERATIONS.md`).
- Only stage intentional changes. `*.key` files, `rconpw`, `groq-api-key.txt`, `jimbo.log`, `jimbo.pid`, and state files remain ignored/untracked.
- The `nemotron` profile is optional and unselected; the owner is not sure it will work out long term.

## Natural Next Action

- Verify the next TOP_DAMAGE request sends a real clickable `[gps=...]` ping in game, then wait for the user's next request.
