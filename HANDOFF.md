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
  `sound_path="utility/research_completed"` and
  `sound=defines.print_sound.use_player_settings` instead of a raw RCON chat
  message, so his messages play only the research-completed chime (no standard
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

- None pending. The post-restart in-game chime on a real Jimbo message is the
  one thing not yet independently confirmed by a player, but the mechanism was
  audibly verified earlier this session.

## Operational Caveats

- Ensure only one instance of Jimbo is running. If restarting, kill the old
  process first (see `docs/OPERATIONS.md`).
- Only stage intentional changes. `*.key` files, `rconpw`, `groq-api-key.txt`,
  `jimbo.log`, `jimbo.pid`, `jimbo_says.log`, and state files remain
  ignored/untracked.
- The old repository (`/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints`)
  used the deprecated `mcrcon` library; do not import its RCON code.

## Natural Next Action

- Wait for the user's next request.
