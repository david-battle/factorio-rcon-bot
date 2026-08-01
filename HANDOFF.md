# Handoff

## Verified State

- Branch: `main`; local commits only (the user pushes manually).
- Jimbo is running under pid `331588` (check `jimbo.pid`), restarted this session
  after killing the previous pid per `docs/OPERATIONS.md`. The Factorio server
  was up; RCON reachable.
- `last_startup_summary.txt` matches the current `startup_change_summary` and the
  startup announcement was sent through the new print mechanism (recorded in
  `jimbo_says.log`).
- See `AGENTS.md`, `docs/OPERATIONS.md`, and `docs/RCON_NOTES.md`. Behavioral
  contracts live in `docs/BOT_CONTRACTS.md`.

## Completed Work

- **Distinct chat notification sound for Jimbo.** Jimbo now delivers every chat
  line through `/silent-command game.forces.player.print(...)` with
  `sound_path="item-move/logistic-robot"` and
  `sound=defines.print_sound.use_player_settings` instead of a raw RCON chat
  message, so his messages play only the inventory-move sound (no standard
  chat ding) and respect each player's chat-sound setting. `send_jimbo_chat()`
  is the single choke point (replies, spontaneous, greetings, startup,
  forget-ack); the sound path is the `jimbo_chat_sound_path` constant.
- **Restart hydration preserved.** `game.print`/`force.print` output is not
  written to `server-console.log`, so every delivered line is appended to the
  gitignored `jimbo_says.log` in the `[CHAT] <server>: Jimbo says ...` format,
  and `hydrate_dialogue()` merges that file's tail with the server log by
  timestamp.
- `docs/RCON_NOTES.md` gained the PrintSettings/SoundPath/`console_message`
  findings; `docs/BOT_CONTRACTS.md` notes the new delivery and hydration
  mechanism; `STARTUP_ANNOUNCEMENTS.md` has the new summary verbatim.

## Validation

- `python -m py_compile jimbo.py` clean; `git diff --check` clean.
- `python -m unittest test_jimbo` ran 118 tests, all passing (3 new: recorded
  `jimbo_says.log` format, hydration merge by timestamp, missing-jimbo-log).
- Live-verified before committing: the `research_completed` chime was audible
  (distinct from the chat ding), and `force.print` output does not appear in
  `server-console.log`.

## Remaining Work

- None pending. The chat sound is `item-move/logistic-robot` (the robotic rattle
  when you move a stack of logistic robots into an inventory) and it is now LIVE:
  Jimbo was restarted on 2026-08-01 ~18:07 under pid `337688` (see `jimbo.pid`)
  and the startup announcement confirmed it. The target sound was confirmed
  audibly this session via a live probe (user confirmed "that it"); note that
  `item-open/logistic-robot` was a dead end because logistic-robot has no
  `open_sound`.

## Current Model

- Jimbo runs on `nemotron` (`nvidia/nemotron-3-ultra-550b-a55b:free` via
  OpenRouter, `openrouter.key`). Switched from `deepseek` (out of quota) on
  request. `openai` (gpt-5.4-mini via OpenCode) failed a live probe with an
  upstream "Unexpected server error"; `nemotron` responded. No token settings
  were changed.

## Operational Caveats

- **2026-08-01 "unresponsive in game" — resolved.** dlbattle reported Jimbo
  "hasn't responded in game". Root cause found and fixed live: `send_jimbo_chat`
  built the `/silent-command game.forces.player.print(...)` command with
  `json.dumps(text)`, whose default `ensure_ascii=True` escapes any emoji/
  non-ASCII character as `\uXXXX`; Factorio's Lua 5.1 has no `\u` escape, so the
  whole print command errored ("invalid escape sequence near '\u'") and nothing
  rendered. `record_jimbo_says()` still logged the line because `client.run()`
  returns the error text as a response instead of raising, masking the failure.
  dlbattle's 14:41:33 reply contained a 😄, so it never displayed. Fix:
  `json.dumps(..., ensure_ascii=False)` (raw UTF-8 is fine in a Lua string
  literal), live-verified with the user seeing the emoji message and hearing the
  chime. 119 unit tests pass (1 new regression test). Requires a restart to take
  effect; `startup_change_summary`/`STARTUP_ANNOUNCEMENTS.md` updated. Note
  `docs/RCON_NOTES.md` documents the `\u`/`ensure_ascii=False` rule. The follow-up
  sound switch to `item-move/logistic-robot` and the `nemotron` model switch are
  now live on pid `337688`.

- Ensure only one instance of Jimbo is running. If restarting, kill the old
  process first (see `docs/OPERATIONS.md`).
- Only stage intentional changes. `*.key` files, `rconpw`, `groq-api-key.txt`,
  `jimbo.log`, `jimbo.pid`, `jimbo_says.log`, and state files remain
  ignored/untracked.
- The old repository (`/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints`)
  used the deprecated `mcrcon` library; do not import its RCON code.

## Natural Next Action

- Wait for the user's next request.
