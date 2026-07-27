# Handoff

## Status

- Branch: `main`.
- Jimbo remains deliberately simple: log input, AI decisions/replies, and RCON.
- The active AI profile remains `openai`, using `openai/gpt-5.4-mini` through
  OpenCode. No provider fallback behavior is implemented.
- Available optional profiles are DeepSeek through OpenCode, Groq GPT-OSS 120B,
  and local Ollama Qwen 2.5 32B. Configuration remains centralized at the top of
  `jimbo.py`; see `OPERATIONS.md` for endpoints and credential handling.

## Completed Work

- Added the optional `groq` profile for `openai/gpt-oss-120b` using the shared
  OpenAI-compatible adapter, low reasoning effort, hidden reasoning, and a
  256-token completion limit.
- Migrated the known working Groq credential to local gitignored
  `groq-api-key.txt` with mode `600`. The credential is intentionally not
  tracked.
- Confirmed the Groq profile through the real adapter with the exact response
  `JIMBO_GROQ_PROFILE_OK`.
- Kept Mistral out of the lineup. Archived and OpenCode Mistral credentials both
  returned HTTP 401, and the owner prefers DeepSeek.
- Documented optional future Jimbo provider fallback in
  `FUTURE_DIRECTIONS.md`; it is an idea only, not current behavior.
- Added `FUTURE_PROJECTS.md` for a separate possible OpenCode model-fallback
  project. OpenCode has no native ordered fallback configuration.
- Added the project OpenCode command `.opencode/command/handoff.md`. Future
  contexts can invoke `/handoff` to review and clean the repository, validate
  changes, refresh this file, stage appropriate files, and create one commit.
- Updated `AGENTS.md` and `OPERATIONS.md` for the new profile and handoff flow.
- Updated `startup_change_summary`; the next Jimbo restart will announce that
  Groq can be selected. Jimbo was not restarted during this context.

## Validation

- `python -m py_compile jimbo.py test_jimbo.py` passed.
- `python -m unittest -v test_jimbo` passed all 20 deterministic tests.
- `git diff --check` passed.
- `opencode debug config` loaded and resolved the new `handoff` command.
- A console-only Groq feasibility request returned the required text in 9.06
  seconds before integration, and the integrated profile check also passed.

Do not use unrestricted `python -m unittest` while the Factorio game client is
running: discovery imports the standalone live `test_ollama.py` smoke script,
which attempts to load the 28 GB local model and currently fails with GPU
out-of-memory. Use the deterministic `test_jimbo` target unless live Ollama
testing is explicitly needed and the game client is closed.

## Current Direction

- Prefer one model per underlying provider where practical.
- Keep Groq optional; changing `ai_profile_name` is still the only way to select
  a different bot model.
- Do not add Mistral or automatic model fallback without a new explicit request.
- Keep Jimbo-specific ideas in `FUTURE_DIRECTIONS.md` and separate projects in
  `FUTURE_PROJECTS.md`.

There are no known pending implementation tasks. The next context should verify
this note against Git, then proceed from the user's next requested change.
