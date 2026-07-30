# Handoff

## Verified State

- Branch: `main`.
- Jimbo is running in the background (`python -u jimbo.py`). The duplicate instances were cleared.
- The `openai/gpt-5.4-mini` profile is currently used.
- See `AGENTS.md` and `docs/OPERATIONS.md` for architecture and running procedures. `docs/BOT_CONTRACTS.md` holds behavioral contracts.

## Completed Work

- **Bugfix for TOP_DAMAGE**: Fixed an issue where tagging the entity with the most products finished would mistakenly tag it as "most launches" (or fail to find the entity) for machines other than the rocket silo. The `run_top_damage_command` in `jimbo.py` now correctly checks for the `products_finished` stat dynamically via `pcall` and falls back to `damage_dealt` if it isn't available.
- Added tests `test_top_damage_decision_parses_and_validates` and `test_top_damage_command_builds_correct_lua` in `test_jimbo.py`.
- Updated `startup_change_summary` in `jimbo.py` and appended the new behavior to `STARTUP_ANNOUNCEMENTS.md`.
- Cleaned up multiple concurrently running Jimbo instances that were echoing responses in game chat, leaving only one running instance.

## Validation

- Ran `python -m unittest test_jimbo` and all 100 tests passed.
- Started Jimbo locally and verified it is running successfully without duplicates.
- Ran `git diff --check` cleanly.

## Remaining Work

- The `TOP_DAMAGE` feature is complete. Wait for the user's next request.

## Operational Caveats

- Ensure only one instance of Jimbo is running. If restarting, make sure the old process is killed (see `docs/OPERATIONS.md`).
- Only stage intentional changes. Ensure credentials and state files remain unstaged.

## Natural Next Action

Wait for the user's next request and proceed accordingly.
