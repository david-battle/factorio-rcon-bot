# Handoff

## Current State

- Branch: `main`; it was one commit ahead of `origin/main` before this handoff.
- Jimbo remains a deliberately simple server-log, AI, and RCON bot implemented
  primarily in `jimbo.py`.
- The active `openai` profile uses `openai/gpt-5.4-mini` through OpenCode.
  DeepSeek, Groq, and local Ollama remain manually selectable profiles; there is
  no automatic provider fallback and Mistral is not configured.
- Owner, provider, model, endpoint, and identity choices remain centralized in
  the top-level configuration block in `jimbo.py`.
- No code or active configuration changed in this context, and no service was
  restarted. The existing `startup_change_summary` remains appropriate for the
  next Jimbo restart.

## Completed Work

- Audited the tracked repository, ignored local artifacts, current
  configuration, operational reference, future-work documents, and recent Git
  history.
- Refreshed this handoff from the verified repository state. No implementation,
  provider, or operational documentation changes were needed.

## Validation

- `python -m py_compile jimbo.py test_jimbo.py` passed.
- `python -m unittest -v test_jimbo` passed all 20 deterministic tests.
- `git diff --check` passed.
- The live `test_ollama.py` smoke was intentionally not run because it can load
  the 28 GB local model and conflict with a running Factorio game client.

## Operational Caveats

- Local credentials, runtime logs, PID/state files, player data, caches, and
  OpenCode dependencies remain ignored and must not be committed.
- Read `OPERATIONS.md` for provider setup, quota history, RCON procedures,
  process management, testing, and runtime recovery details.

## Next Action

There are no pending implementation tasks or known blockers. Verify this note
against Git and proceed from the user's next request. Preserve one model per
underlying provider where practical, keep Groq optional, and do not add Mistral
or automatic fallback without an explicit request.
