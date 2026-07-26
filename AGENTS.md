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
  Also present: `[JOIN]` PlayerName joined the game and `[LEAVE]`.
- To extract message text: split on `[CHAT] ` first, then on `: ` (timestamp has colons).
  The username is also extracted; used for chat history context and known_players tracking.
- Skip any line where msg starts with "Jimbo says " (bot's own echo).
- The AI model decides whether the message is addressed to Jimbo.
- `[JOIN]` lines trigger a model-generated greeting (new vs returning via known_players.txt).

## Request flow, step by step
1. Listener sees a new `[CHAT]` line and extracts (username, message text).
2. Ask the AI model: does this need info from the server? Model replies: SKIP (not addressed), NONE (addressed but no data needed), PLATFORMS, PLANETS, or a built-in command.
3. If PLATFORMS or PLANETS, run the corresponding canned `/silent-command` with `rcon.print()` (see below). If a built-in command, run it.
4. Send the RCON response back to the AI model, ask it to compose a short reply in plain chat-appropriate language.
5. Send that reply via RCON as a raw command (no `/`) so it appears as `[CHAT] <server>: Jimbo says ...` in the log.
6. Step 3 also has a "SKIP" output option — model can say SKIP to stay silent during reply generation as a second-pass filter.

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

## Testing approach (offline simulation)

Nobody needs to log into the game to test. The bot tails the server log, so you can
simulate activity by appending lines to `/mnt/d/factorio-server/server-console.log`:

```bash
printf '%s [CHAT] dlbattle: Jimbo what is the evolution factor?\n' "$(date '+%Y-%m-%d %H:%M:%S')" >> /mnt/d/factorio-server/server-console.log
```

The bot will pick up the line, process it through the AI pipeline, and attempt to
send a reply via RCON. Watch the bot log:

```bash
tail -f chat_monitor.log
```

To test JOIN greetings:
```bash
printf '%s [JOIN] TestPlayer joined the game\n' "$(date '+%Y-%m-%d %H:%M:%S')" >> /mnt/d/factorio-server/server-console.log
```

### Cold start caveat

The local model (qwen2.5-32b-ctx32k, 28 GB) takes 30-60 seconds to load into
GPU memory on first request after idle. Check if the model is loaded from the
Windows side:

```bash
ollama.exe ps
```

If the model isn't listed, expect the first response to take up to a minute.
Subsequent requests are faster but the model is still slow — budget ~20-45
seconds per LLM call. Do NOT queue multiple test messages rapidly; the model
will serialize them and the responses will be delayed and confusing.

### Model memory constraint

The game client and the local model cannot run on the same machine at the same
time — they don't fit in memory together. The server (Windows native) and the
model (WSL/Ollama) can coexist because they're on different OS instances.

## Known pitfalls

### Cross-filesystem file handle invalidation

The server log at `/mnt/d/factorio-server/server-console.log` lives on a Windows
drive mounted in WSL. Writing to the file from the Windows side (e.g., when the
bot sends an RCON command and the server logs it) can invalidate the WSL file
descriptor. This crashes `f.tell()` with `ValueError: I/O operation on closed
file`. The bot handles this by catching OSError on read operations and reopening
the file.

### RCON multi-line messages

Sending a multi-line string via `client.run(f"Jimbo says {reply}")` only delivers
the first line. To send multiple lines, split by `\n` and send each as a separate
RCON command:
```python
for line in reply.split("\n"):
    if line.strip():
        client.run(f"Jimbo says {line.strip()}")
```

### Platform/ship name quality

Space platform names on this server include cargo descriptions and signal markup
(e.g., `[item=space-science-pack]`, `[planet=nauvis][planet=vulcanus]Sausage`).
The step 3 prompt instructs the model to strip `[item=...]`, `[planet=...]`,
`[virtual-signal=...]`, `[space-location=...]` brackets but keep the rest. The
model should list EVERY line from the RCON response when asked, not just the ones
it thinks look like platform names.

### known_players.txt seeding

Seed from the RCON `/players` command (lists everyone who has ever played this save).
Do this once on initial setup; the bot appends new players automatically as they join.
Only reseed if: (1) the save file is replaced/reset, (2) the file is lost, or
(3) you want to flush test/debris entries accumulated from offline testing:
```python
from rcon.source import Client
with open("rconpw") as f:
    password = f.read().strip()
with Client("127.0.0.1", 27015, passwd=password) as client:
    raw = client.run("/players")
    with open("known_players.txt", "w") as out:
        for line in raw.split("\n"):
            line = line.strip()
            if line and not line.startswith("Players"):
                out.write(line + "\n")
```
One-off bash version:
```bash
python3 -c "
from rcon.source import Client
with open('rconpw') as f: pw = f.read().strip()
with Client('127.0.0.1', 27015, passwd=pw) as c:
    raw = c.run('/players')
    with open('known_players.txt', 'w') as out:
        for line in raw.split('\n'):
            line = line.strip()
            if line and not line.startswith('Players'):
                out.write(line + '\n')
"

## Current implementation status

All three steps from IMPLEMENTATION.md are present in chat_monitor.py:
the chat listener, the AI decision loop, and the RCON query/send cycle.
They work end-to-end but can be rough around the edges — expect iterative
tuning rather than fundamental rewrites.

## Keep working
For clear, reversible tasks, act immediately after a brief plan; do not wait for “go ahead.” Ask first only when requirements are ambiguous or an action is destructive.
