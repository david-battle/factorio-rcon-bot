# Handoff

## Verified State

- Branch: `main`; local commits only (the user pushes manually).
- **Jimbo is running** under pid `353102` (see `jimbo.pid`), started 2026-08-03
  11:03, verified alive (single instance). The launcher via `setsid` forks, so
  re-confirm the recorded PID with `ps` from a fresh session.
- **Jimbo runs on `big-pickle`** via OpenCode Zen (OpenAI-compatible,
  `https://opencode.ai/zen/v1`, `auth_provider=opencode` reading
  `~/.local/share/opencode/auth.json`; never read or print a token),
  `max_completion_tokens: 4096`.
- `last_startup_summary.txt` matches the current `startup_change_summary`
  ("I now remember about 40 minutes of recent chat instead of 15..."), so the
  running process already announced the latest change and no further
  `STARTUP_ANNOUNCEMENTS.md` entry is needed for another restart of this same
  code.
- This session's changes are **uncommitted** (jimbo.py, test_jimbo.py,
  STARTUP_ANNOUNCEMENTS.md, docs/BOT_CONTRACTS.md, docs/RCON_NOTES.md,
  docs/FUTURE_DIRECTIONS.md). Last commit: `b6729fb`.

## Completed Work

### Map-tag `all` surfaces + corpse tagging (root cause fix)

Moon-O-Cronic's "Jimbo please tag all player corpses" failed with
`LuaGameScript doesn't contain key create_chart_tag`: the structured
`TAG|surface|entity-type|label` flow only accepted a named surface, so the
model improvised raw Lua across all surfaces with a nonexistent API.

- `run_tag_command` / `run_untag_command` (jimbo.py) now accept
  `surface="all"` and iterate `pairs(game.surfaces)`, mirroring LOGISTICS'
  existing `all` handling. Single-surface output format is unchanged.
  All-surface output reports `per-surface:count` chunks, e.g.
  `Tagged 4 character-corpse on nauvis:4`.
- Classifier prompt (both the available-commands list and the decision list)
  now teaches that player corpses use entity type `character-corpse` and that
  TAG/UNTAG accept surface `all`.
- Reply prompts now hint at per-surface breakdowns when `all` was scanned.
- Verified live (read-only): `character-corpse` is a valid entity prototype;
  4 corpses on nauvis found by both `name` and `type` filters. The chart-tag
  API is `game.forces.player.add_chart_tag`, not `game.create_chart_tag`.
- After the restart, Moon's re-request succeeded: "Tagged all 4 player corpses
  on Nauvis."

### Dialogue memory window: 15 -> 40 minutes

dlbattle noticed the corpse request was outside Jimbo's 15-minute dialogue
window at restart, so hydration dropped it (by design). With sparse in-game
chat, the owner asked to widen it:

- `dialogue_max_age = 40 * 60` (jimbo.py config block).
- Updated `docs/BOT_CONTRACTS.md` and `docs/FUTURE_DIRECTIONS.md` (12 turns,
  40 minutes, ~4000 chars).
- Updated two test boundaries that assumed the old 900s cutoff
  (`now - 901` -> `now - 2401`; `now - 1000` -> `now - 2500`).
- After restart, hydration restored 12 recent turns (the corpse exchange was
  back in reach).

## Validation

- `python -m py_compile jimbo.py` clean; `git diff --check` clean.
- `python -m unittest test_jimbo` — 127 tests, all passing (4 added this
  session for corpse/all-surface tagging, 2 updated command assertions, 2
  age-boundary updates).
- Not run: `test_ollama.py` (per operations guidance, avoid while the Factorio
  client uses the GPU).

## Remaining Work

- None pending. If a future request needs a different entity type with an
  uncertain internal name, the `pairs()` + `:find()` enumeration guidance in
  the classifier prompt should cover it.
- Residual limitation (from prior handoffs, unchanged): `TAG` cannot filter
  assembling machines by current recipe. See `docs/FUTURE_DIRECTIONS.md`.

## Current Model

- `big-pickle` (free) via OpenCode Zen, OpenAI-compatible adapter,
  `max_completion_tokens: 4096`, auth via OpenCode's `opencode` credential.
  Unchanged this session.

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
