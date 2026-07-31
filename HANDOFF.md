# Handoff

## Verified State

- Branch: `main`.
- Jimbo is running in the background (`python -u jimbo.py`, PID 311730); single instance.
- The `deepseek` profile (`deepseek-v4-flash-free` via the OpenCode AI API) is currently used.
- `last_startup_summary.txt` matches the current `startup_change_summary`.
- See `AGENTS.md` and `docs/OPERATIONS.md` for architecture and running procedures. `docs/BOT_CONTRACTS.md` holds behavioral contracts.

## Completed Work

- **RCON/Lua knowledge consolidated** (uncommitted, this handoff): `docs/RCON_NOTES.md` is now the canonical RCON/Lua reference. It gained Connection, Command Reference, Map Pings, Query Idioms, Verified Runtime Facts, and Built-in Jimbo Queries sections. Facts were moved from `docs/OPERATIONS.md` (command reference, map pings) and summarized from `docs/FUTURE_DIRECTIONS.md` live findings and `jimbo.py`'s query implementations. `AGENTS.md` now requires reading it before composing new RCON/Lua queries and adding learnings back to it.
- Doc-only work; `jimbo.py` and behavior unchanged. No startup-change announcement needed (no code change).

## Validation

- Ran `python -m unittest test_jimbo`: all 108 tests passed.
- Ran `python -m py_compile` on `jimbo.py` and `test_jimbo.py`; clean.
- Ran `git diff --check`; clean. `test_ollama.py` was not run (live, needs the GPU).

## Remaining Work

- None pending from this session. `docs/RCON_NOTES.md` is untracked until this handoff's commit; it will be committed along with the doc edits.

## Operational Caveats

- Ensure only one instance of Jimbo is running. If restarting, kill the old process first (see `docs/OPERATIONS.md`).
- Only stage intentional changes. `*.key` files, `rconpw`, `groq-api-key.txt`, `jimbo.log`, `jimbo.pid`, and state files remain ignored/untracked.
- The old repository (`/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints`) used the deprecated `mcrcon` library; do not import its RCON code.

## Natural Next Action

- Wait for the user's next request.
