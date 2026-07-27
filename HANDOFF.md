# Handoff

## Current State

- Branch: `main`.
- Jimbo remains a deliberately simple server-log, AI, and RCON bot implemented
  primarily in `jimbo.py`.
- The active `openai` profile uses `openai/gpt-5.4-mini` through OpenCode.
  DeepSeek, Groq, and local Ollama remain manually selectable profiles; there is
  no automatic provider fallback and Mistral is not configured.
- Owner, provider, model, and endpoint choices remain centralized in the
  top-level configuration block in `jimbo.py`.
- No code or active configuration changed in this context, and no service was
  restarted. The existing `startup_change_summary` remains appropriate for the
  next Jimbo restart.

## Completed Work

- Investigated the earlier repository at
  `/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints` for Gemini history.
- Recorded the verified findings in `OPERATIONS.md`: Gemini was briefly used for
  development through Google Antigravity; the old bot implemented
  `gemini-2.5-flash` as a fallback, but retained logs do not prove that a live
  Jimbo response used it.
- Documented the current Antigravity quota policy: ordinary free quota refreshes
  weekly, while paid baseline quota refreshes every five hours until its weekly
  limit. The policy link and quota-check commands are in `OPERATIONS.md` because
  limits may change.

## Validation

- `python -m py_compile jimbo.py test_jimbo.py` passed.
- `python -m unittest -v test_jimbo` passed all 20 deterministic tests.
- `git diff --check` passed.
- The live `test_ollama.py` smoke was intentionally not run because it can load
  the 28 GB local model and conflict with a running Factorio game client.

## Next Action

There are no pending implementation tasks or known blockers. Verify this note
against Git, read `OPERATIONS.md` for provider and runtime details when relevant,
and proceed from the user's next request. Preserve one model per underlying
provider where practical, keep Groq optional, and do not add Mistral or automatic
fallback without an explicit request.
