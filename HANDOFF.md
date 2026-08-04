# Handoff

## Verified State

- Branch: `main`; local commits only (the user pushes manually).
- **Jimbo is running** under pid `357147` (see `jimbo.pid`), verified alive.
  The launcher via `setsid` forks, so re-confirm the recorded PID with `ps`
  from a fresh session.
- **Jimbo runs on `big-pickle`** via OpenCode Zen (OpenAI-compatible,
  `https://opencode.ai/zen/v1`, `auth_provider=opencode` reading
  `~/.local/share/opencode/auth.json`; never read or print a token),
  `max_completion_tokens: 4096`.
- `last_startup_summary.txt` matches the current `startup_change_summary`
  ("I now remember about 40 minutes of recent chat instead of 15..."), so no
  further `STARTUP_ANNOUNCEMENTS.md` entry is needed. The two prompt-only
  fixes below take effect on the next message, not on restart, so no startup
  announcement was warranted for them.
- All tracked changes are committed; the worktree is clean. Pending the
  user's manual push.

## Completed Work

### GPS entity-lookup fix (prompt + notes, this session)

A player asked "what is this work of art at [gps=-125.5,143.4]?" and Jimbo
replied that it could not run the lookup because the model invented
`LuaSurface.find_entity_at_position`, which does not exist on 2.1.12. The
classification prompt now teaches the correct pattern:
`find_entities_filtered{position={x,y}}` (entities whose collision box covers
that position) or with `radius=1`; `find_entity(name, position)` requires a
name. Recorded in `docs/RCON_NOTES.md`. The player later confirmed the fix
worked ("Interesting.").

### Soft resistance to cheating (prompt + contract, this session)

After BSG_G, darklich14, and SilentLog repeatedly talked Jimbo into cheats —
spawning an infinity-chest and a behemoth-biter, inserting legendary mech
armor/exoskeletons into players, teleporting a player to Vulcanus lava, and
giving items — the user asked for **soft, prompt-level resistance**: no Python
enforcement, no absolute filter, tolerating players who talk around it, and no
owner exemption.

- Classification prompt (`build_classification_prompt`): decline in character
  requests to spawn/grant items or entities, insert equipment into anyone,
  teleport players, or bypass progression; offer legitimate alternatives
  (tags, untags, logistics, research/recipes, translations). Explicitly soft,
  no lecturing, never announces the policy.
- `NONE` reply hint (`build_reply_prompt`): same decline guidance for chat-only
  replies.
- Documented in `docs/BOT_CONTRACTS.md` ("Cheating Resistance" section).
- Live behavior verified in `jimbo.log`: Jimbo now declines teleport requests
  from `dlbattle`, `BSG_G`, and others, offering map tags instead.

## Validation

- `python -m py_compile jimbo.py` clean; `git diff --check` clean.
- `python -m pytest test_jimbo.py -q`: **127 passed, 43 subtests passed**
  (run after all prompt edits).
- Not run: `test_ollama.py` (per operations guidance, avoid while the Factorio
  client uses the GPU).
- The GPS fix and the soft-resistance behavior were both confirmed live in
  chat/logs after the edits.

## Remaining Work

- None pending in code. The soft resistance is intentionally porous by design
  (players may talk around it); if the user later wants stronger enforcement,
  that would be a deliberate escalation, not a bug.
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
- Prompt edits take effect immediately (the prompt is rebuilt per message);
  only code that matters at startup warrants a `startup_change_summary` bump.
- Only stage intentional changes. `*.key`, `rconpw`, `groq-api-key.txt`,
  `jimbo.log`, `jimbo.pid`, `jimbo_says.log`, `last_*.txt`, and
  `known_players.txt` remain ignored/untracked.
- The old repository (`/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints`)
  used the deprecated `mcrcon` library; do not import its RCON code.
- `LuaSpacePlatform.get_imports()`/`get_requesting()` are gone in 2.1.12; use
  `platform.hub.get_logistic_sections()` for platform requests. See
  `docs/RCON_NOTES.md`.

## Natural Next Action

- Wait for the user's next request. The handoff commit below should be pushed
  only when the user asks.
