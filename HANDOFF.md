# Handoff

## Verified State

- Branch: `main`; local commits only (the user pushes manually).
- **Jimbo is running** under pid `353102` (see `jimbo.pid`), verified alive.
  The launcher via `setsid` forks, so re-confirm the recorded PID with `ps`
  from a fresh session.
- **Jimbo runs on `big-pickle`** via OpenCode Zen (OpenAI-compatible,
  `https://opencode.ai/zen/v1`, `auth_provider=opencode` reading
  `~/.local/share/opencode/auth.json`; never read or print a token),
  `max_completion_tokens: 4096`.
- `last_startup_summary.txt` matches the current `startup_change_summary`
  ("I now remember about 40 minutes of recent chat instead of 15..."), so the
  running process already announced the latest change and no further
  `STARTUP_ANNOUNCEMENTS.md` entry is needed for another restart of this same
  code.
- All changes to date are committed; the tracked worktree is clean. This
  session's doc change (handoff procedure) is committed separately pending the
  user's manual push.

## Completed Work

### Handoff procedure: next context expects committed state

The prior handoff's note said "This session's changes are uncommitted", but
`HANDOFF.md` is committed together with the code and a fresh context reads it
only after the user reviews and pushes. That framing was therefore stale by the
time it was verified.

- `docs/HANDOFF_PROCEDURE.md` (both Heavy step 8 and Light step 4) now
  instructs the handoff note to describe the repository as it will be at
  handoff time: changes committed, tracked worktree clean, pending the user's
  manual push. Never label work "uncommitted". A preamble paragraph explains
  why (the note is read after the user's push; if a hash is needed, reference
  the previous commit since the note is written before its own commit).
- This session's earlier `HANDOFF.md` stale-line fix is folded into the rewrite
  below.

### Map-tag `all` surfaces + corpse tagging (prior session, committed `112dd28`)

- TAG/UNTAG accept `surface="all"` and iterate `pairs(game.surfaces)`;
  classifier prompt teaches `character-corpse` and the `all` surface.
- Chart-tag API is `game.forces.player.add_chart_tag`, not
  `game.create_chart_tag`. See `docs/RCON_NOTES.md`.
- Dialogue memory window widened 15 -> 40 minutes (`dialogue_max_age`), 12
  turns, ~4000 chars.

## Validation

- This session: doc-only change; `git diff --check` clean. No tests rerun
  (nothing behavior-changing). Not run: `test_ollama.py` (per operations
  guidance, avoid while the Factorio client uses the GPU).
- Prior session (`112dd28`): `python -m py_compile jimbo.py` clean;
  `python -m unittest test_jimbo` — 127 tests passing.

## Remaining Work

- None pending. If a future request needs an entity type with an uncertain
  internal name, the `pairs()` + `:find()` enumeration guidance in the
  classifier prompt should cover it.
- Residual limitation (from prior handoffs, unchanged): `TAG` cannot filter
  assembling machines by current recipe. See `docs/FUTURE_DIRECTIONS.md`.

## Current Model

- `big-pickle` (free) via OpenCode Zen, OpenAI-compatible adapter,
  `max_completion_tokens: 4096`, auth via OpenCode's `opencode` credential.
  Unchanged.

## Operational Caveats

- Ensure only one Jimbo instance. If restarting, kill the old process first
  (see `docs/OPERATIONS.md`); `setsid` forks so the recorded `$!` may be the
  wrapper — re-check with `ps`.
- Only stage intentional changes. `*.key`, `rconpw`, `groq-api-key.txt`,
  `jimbo.log`, `jimbo.pid`, `jimbo_says.log`, `last_*.txt`, and
  `known_players.txt` remain ignored/untracked.
- The old repository (`/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints`)
  used the deprecated `mcrcon` library; do not import its RCON code.
- `game.create_chart_tag` does not exist on 2.1.12; use
  `game.forces.player.add_chart_tag`. See `docs/RCON_NOTES.md` for the corpse
  entity facts and the `all`-surface iteration note.

## Natural Next Action

- Wait for the user's next request. The handoff commit below should be pushed
  only when the user asks.
