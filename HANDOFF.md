# Handoff

## Current State

- Branch: `main`; before this handoff commit it was two commits ahead of
  `origin/main`.
- Jimbo remains the deliberately simple server-log, AI decision/reply, and RCON
  bot in `jimbo.py`. Runtime code and configuration did not change.
- The active profile remains `openai/gpt-5.4-mini` through OpenCode. DeepSeek,
  Groq, and local Ollama remain manually selectable with no automatic fallback.

## Completed Work

- Audited every project-authored Markdown file and removed or condensed obsolete,
  duplicated, transient, and save-specific operational detail selected by the
  user.
- Reduced `OPERATIONS.md` from about 6,380 to 3,867 `o200k_base` tokens while
  retaining RCON, placement safety, rollback, provider, checkpoint, testing, and
  player-seeding procedures. The Local Ollama section and `SYSTEM_ADMIN.md` were
  intentionally left unchanged.
- Replaced the completed 2,358-token conversational implementation plan with a
  515-token record of current invariants and validation coverage.
- Deleted the obsolete completed `IMPLEMENTATION.md` plan.
- Added authoritative root-level `HANDOFF_PROCEDURE.md` for any coding agent.
  `AGENTS.md` points to it, and `.opencode/command/handoff.md` is now only an
  OpenCode wrapper around the shared procedure.

## Validation

- `python -m py_compile jimbo.py test_jimbo.py` passed.
- `python -m unittest -v test_jimbo` passed all 25 deterministic tests.
- `git diff --check` passed.
- No Jimbo code changed, so no startup-summary update or service restart is
  required.

## Remaining Work

- No follow-up is required for this documentation cleanup.
- Continue normal user-directed Jimbo work. Read `OPERATIONS.md` only for the
  operational topics listed in `AGENTS.md`, and follow `HANDOFF_PROCEDURE.md` for
  future handoffs.

## Operational Caveats

- Do not restart Jimbo, Factorio, or another service merely to resume work.
- Credentials, runtime logs, PID/state files, player data, caches, and local
  OpenCode dependencies remain ignored and must not be committed.
