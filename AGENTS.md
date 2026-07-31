# Jimbo — Factorio RCON Bot

Jimbo is a deliberately simple Factorio bot: it reads server activity, asks an
AI model what to do, then uses RCON for queries and chat replies. Keep changes
small. Do not add unrequested infrastructure such as databases, web servers, or
configuration frameworks.

## Start here

- Before editing code, read `docs/OPERATIONS.md` for setup, RCON, providers,
  testing, deployment, and runtime diagnosis.
- Before composing any new RCON or Lua query, read `docs/RCON_NOTES.md`. Add new
  RCON/Lua learnings back to that file, as briefly as possible.
- Read `docs/BOT_CONTRACTS.md` before changing chat behavior, RCON
  actions, production cells, dialogue, startup announcements, or spontaneous
  comments.
- When resuming after `/handoff`, read `HANDOFF.md` and verify it against Git
  and the current files. This file remains authoritative.
- When preparing a handoff, follow `docs/HANDOFF_PROCEDURE.md`.
- Before planning a Jimbo feature based on live experiments, read
  `docs/FUTURE_DIRECTIONS.md`.

## Always preserve

- Keep owner, model, and provider choices in `jimbo.py`'s one top-level
  configuration block (`server_owner`, `ai_profile_name`, and `ai_profiles`).
  Do not scatter those values through the code.
- The development assistant is not Jimbo. Report any direct RCON work as an
  assistant action, even when using the in-game `Jimbo says ` prefix.
- If a code change will take effect on restart, update
  `startup_change_summary` and append its exact text to
  `STARTUP_ANNOUNCEMENTS.md` in the same edit.
- Validate Python changes with `python -m py_compile`; use relevant deterministic
  tests as described in Operations. Ask rather than inventing missing
  project-specific values.
