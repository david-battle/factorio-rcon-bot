# Handoff

## Verified State

- Branch: `main`; local commits only (the user pushes manually).
- Jimbo's running state was NOT verified this session (no `jimbo.py` process was
  found when checked; the server itself was up, since RCON probes succeeded).
- The `deepseek` profile (`deepseek-v4-flash-free` via the OpenCode AI API) is used.
- `last_startup_summary.txt` matches the current `startup_change_summary`.
- See `AGENTS.md` and `docs/OPERATIONS.md` for architecture and running procedures.
  `docs/BOT_CONTRACTS.md` holds behavioral contracts.

## Completed Work

- **RCON/Lua facts corrected in `docs/RCON_NOTES.md`** (live-verified against the
  running server):
  - `defines.entity_status` maps name->number; `defines.entity_status[e.status]`
    returns nil, so compare against a named constant or reverse-map with `pairs()`.
  - Embedded `\n` in `rcon.print` output IS delivered intact; the real limit is a
    ~4 KB single response (~6 KB hung the `rcon.source` client). The old
    "only the first line" claims were removed from Tooling and `docs/OPERATIONS.md`.
  - Yesterday's uncommitted learnings (recipe/tech/status/area/logistic-filter
    idioms) reviewed against probe files in `/tmp/opencode` and committed.
- **Light handoff procedure** added to `docs/HANDOFF_PROCEDURE.md`; both procedures
  now state the user always pushes manually.
- Doc-only work; `jimbo.py` and behavior unchanged. No startup-change announcement
  needed (no code change).

## Validation

- Live RCON probes: newline survival, ~4 KB response boundary, `defines.entity_status`
  numeric-index nil check.
- `git diff --check` clean.
- NOT run: `python -m unittest test_jimbo` and `py_compile` (light handoff; no code
  changes this session).

## Remaining Work

- None pending. All three doc edits are committed in this handoff's commit.

## Operational Caveats

- Ensure only one instance of Jimbo is running. If restarting, kill the old process
  first (see `docs/OPERATIONS.md`).
- Only stage intentional changes. `*.key` files, `rconpw`, `groq-api-key.txt`,
  `jimbo.log`, `jimbo.pid`, and state files remain ignored/untracked.
- The old repository (`/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints`) used
  the deprecated `mcrcon` library; do not import its RCON code.

## Natural Next Action

- Wait for the user's next request.
