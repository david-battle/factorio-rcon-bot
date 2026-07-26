# Jimbo — Factorio RCON Bot

## Repo
Git repo at ~/factorio-rcon-bot, branch `main`.

## Scope
This bot connects to a running Factorio dedicated server via RCON and lets
players/admins run commands and query game state. Keep it simple — this is
a rebuild specifically to avoid the complexity that broke the previous
version. Don't add features beyond what's asked.

## Environment
- Bot code lives in WSL's native Linux filesystem (~/factorio-rcon-bot),
  NOT under /mnt/c or /mnt/d.
- The Factorio dedicated server itself runs natively on Windows
  (D:\factorio-server, started via ss.bat) and CANNOT be moved into WSL.
- The bot therefore connects to the server across the WSL <-> Windows
  boundary via RCON over the network (host 127.0.0.1, see below) — it does
  not share a filesystem with the server process.
- Python dependencies are managed in a single shared venv at
  /mnt/d/.venv (auto-activated via .bashrc), not a per-project venv.

## RCON Connection — VERIFIED, DO NOT SUBSTITUTE
- Library: `rcon` (installed via `pip install rcon`), specifically the
  `rcon.source` module. Do NOT use `mcrcon` or any other RCON library —
  this exact package was tested and confirmed working.
- Host: 127.0.0.1 (loopback — the bot and the RCON port are on the same
  machine from the server's perspective)
- Port: 27015 (Factorio's default RCON port — confirmed, not assumed)
- Password: stored in ./rconpw (copied from the server's actual config,
  gitignored — never hardcode the password or commit this file)

Verified working connection pattern:
```python
from rcon.source import Client

with open("rconpw") as f:
    password = f.read().strip()

with Client("127.0.0.1", 27015, passwd=password) as client:
    response = client.run("/players")
    print(response)
```

## Architecture — only 3 moving parts
1. The server log file (chat input)
2. The local AI model (decides what to do, composes RCON queries and replies)
3. RCON (send queries/actions, send replies)

Nothing else. Keep it this simple — do not add a database, web server,
config framework, or anything not listed here unless explicitly asked.

## Chat listener
- Tail this file for new lines: /mnt/d/factorio-server/server-console.log
- Log line format (confirmed from live server output):
  `YYYY-MM-DD HH:MM:SS [CHAT] username: message text`
  Also present: `[JOIN]` and `[LEAVE]` lines — ignore these for now.
- To extract message text: split on `[CHAT] ` first, then on `: ` (timestamp has colons).
- Skip any line where msg starts with "Jimbo says " (bot's own echo).
- The AI model decides whether the message is addressed to Jimbo.

## Request flow, step by step
1. Listener sees a new `[CHAT]` line and extracts (username, message text).
2. Ask the AI model: does this need info from the server? Model replies: SKIP (not addressed), NONE (addressed but no data needed), PLATFORMS, PLANETS, or a built-in command.
3. If PLATFORMS or PLANETS, run the corresponding canned `/silent-command` with `rcon.print()` (see below). If a built-in command, run it.
4. Send the RCON response back to the AI model, ask it to compose a short reply in plain chat-appropriate language.
5. Send that reply via RCON as a raw command (no `/`) so it appears as `[CHAT] <server>: Jimbo says ...` in the log.
6. Script also has a keyword fallback: if model says NONE but message mentions ships/platforms/planets, trigger the canned query anyway.

## Useful RCON commands (starting hints — keep this list small)
- `/players` — list all players who have ever played on this save
- `/players online` — list currently connected players only
- `/evolution` — check enemy evolution factor
- `/time` — server uptime and game time (returns "X hours, Y minutes and Z seconds")
- To send a chat message FROM the bot: just send the raw text as the RCON command (no `/prefix`), it appears as `[CHAT] <server>: ...` in the log and in-game.
- `/c` and `/silent-command` with plain Lua usually return nothing over RCON. Use `rcon.print()` inside Lua to get data back.

## Canned RCON queries (hardcoded, model just chooses which to run)
- **PLATFORMS** (space platforms/ships):
  `/silent-command local list={};for _,surface in pairs(game.surfaces) do if surface.platform then table.insert(list,surface.platform.name) end end;rcon.print(table.concat(list,"\n"))`
- **PLANETS**:
  `/silent-command local list={};for _,surface in pairs(game.surfaces) do if surface.planet then table.insert(list, surface.planet.name:sub(1,1):upper()..surface.planet.name:sub(2)) end end;rcon.print(table.concat(list,"\n"))`

## Ground rules for the assistant working on this project
- If something needed (a file, a value, a detail) isn't in this document,
  ASK rather than guessing or inventing a plausible-sounding default.
- If you're not sure whether something is still accurate, say so — don't
  present an assumption as a fact.

## Local AI

A local Ollama model is available at `http://127.0.0.1:11434`:

```python
from ollama import Client
reply = Client(host="http://127.0.0.1:11434").chat(
    model="qwen2.5-32b-ctx32k",
    messages=[{"role": "user", "content": prompt}],
)
text = reply.message.content
```

## Fixing indentation errors in python
For an unparseable Python file, output and replace the complete enclosing function or file using the Write tool; do not use Edit for whitespace repairs. Then validate with `python -m py_compile`.

## Flushing output in python
For long-running monitors and redirected output, use `print(..., flush=True)` so output appears immediately.


## Running monitoring programs that run indefinitely
Run long-lived programs in the background so work can continue. Detach all standard streams and save the PID:

`nohup python -u program.py </dev/null >program.log 2>&1 & echo $! >program.pid`

Verify with `ps -p "$(cat program.pid)"`; don’t wait for the process to exit.

## Current implementation status

All three steps from IMPLEMENTATION.md are present in chat_monitor.py:
the chat listener, the AI decision loop, and the RCON query/send cycle.
They work end-to-end but can be rough around the edges — expect iterative
tuning rather than fundamental rewrites.

## Keep working
For clear, reversible tasks, act immediately after a brief plan; do not wait for “go ahead.” Ask first only when requirements are ambiguous or an action is destructive.
