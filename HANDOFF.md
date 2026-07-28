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

- Successful direct replies now consume the spontaneous activity backlog while
  remaining available in bounded shared dialogue.
- The classifier prompt can return arbitrary Factorio slash commands for
  explicit actions and requires custom Lua actions to print their actual result.
- Scheduled commentary stays silent with no connected players. Active research
  that remains unchanged across online checks gets one deterministic stall
  notice, then no repeated research notices until it changes.
- Added tests for backlog consumption, custom action prompting, empty-server
  silence, one-time stall notices, and resumed research.
- Moved recurring assistant-versus-Jimbo identity guidance into `AGENTS.md`,
  added the local chat-review marker to `.gitignore`, and documented verified
  RCON techniques and future grounded GPS/action work in the appropriate files.

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
- The expanded custom slash-command prompt has deterministic prompt coverage but
  has not yet been exercised by a new live actionable request through the running
  Jimbo process.

## Operational Caveats

- Jimbo was restarted during this context and the current startup summary has
  already been announced. Do not restart any service merely to resume work.
- Credentials, runtime logs, PID/state files, player data, caches, and the chat
  review marker remain ignored and must not be committed.
- Read `OPERATIONS.md` for provider setup, process management, testing, save
  recovery, and detailed verified RCON procedures.
