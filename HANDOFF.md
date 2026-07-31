# Handoff

## Verified State

- Branch: `main`.
- Jimbo is running in the background (`python -u jimbo.py`, PID 311730); single instance.
- The `deepseek` profile (`deepseek-v4-flash-free` via the OpenCode AI API) is currently used.
- `last_startup_summary.txt` matches the current `startup_change_summary`; the untag change was announced on the last restart (22:08).
- See `AGENTS.md` and `docs/OPERATIONS.md` for architecture and running procedures. `docs/BOT_CONTRACTS.md` holds behavioral contracts.

## Completed Work

- **TOP_DAMAGE map ping fix** (committed as `09f22a6`): the top-entity command now emits an exact `[gps=x,y,surface]`, the reply prompt requires it verbatim, and `ensure_gps_ping()` deterministically appends a ping line if the model omits it. Verified live in game.
- **UNTAG fix** (uncommitted, this handoff): TOP_DAMAGE chart-tag text is now `<entity-name> <unit-number> highest <stat>: <value>` (e.g. `foundry 771429 highest products: 938421`), and `run_untag_command` matches label prefixes instead of exact text. Jimbo can now remove its own tags — verified live (tag assembling-machine-3, then `UNTAG` removed 1 tag). Prompt guidance and `docs/BOT_CONTRACTS.md` updated.
- **Provider work** (committed): switched to `deepseek`, added a `nemotron` profile (left configured, unselected), added `*.key` to `.gitignore`, fixed profile-set tests, updated `docs/OPERATIONS.md`.
- **Known limitation (accepted)**: UNTAG matches by tag *text* prefix, not map location, so a GPS-pinged location with tags under a different name won't be found. The owner called this "good enough." Fuzzy "I'm talking to Jimbo but forgot his name" triggering was explicitly declined (chat-spam risk).

## Validation

- Ran `python -m unittest test_jimbo`: all 108 tests passed (includes the 3 new UNTAG tests).
- Ran `python -m py_compile` on `jimbo.py` and `test_jimbo.py`; clean.
- Ran `git diff --check`; clean. `test_ollama.py` was not run (live, needs the GPU).

## Remaining Work

- None pending from this session.

## Operational Caveats

- Ensure only one instance of Jimbo is running. If restarting, kill the old process first (see `docs/OPERATIONS.md`).
- Only stage intentional changes. `*.key` files, `rconpw`, `groq-api-key.txt`, `jimbo.log`, `jimbo.pid`, and state files remain ignored/untracked.
- The `nemotron` profile is optional and unselected.

## Natural Next Action

- Wait for the user's next request. The owner has been testing tag/ping/untag flows in game and is satisfied with the current behavior.
