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
2. The AI model (decides what to do, composes RCON queries and replies)
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

### Intentional model flexibility

The classifier may return any slash command and the bot will pass it through to
RCON. This is intentional: flexibility is a goal, and restricting commands to a
fixed whitelist is a non-goal. Do not add a command whitelist unless explicitly
asked. Jimbo may also jokingly claim an action is underway when no RCON action
occurred; this occasional error is considered part of the bot's humor, not a
problem that needs guardrails.

## AI Provider

Uses **OpenAI GPT-5.4 Mini** through OpenCode's authenticated OpenAI provider:

- Model: `openai/gpt-5.4-mini`
- Auth: OpenCode's configured `openai` provider in
  `~/.local/share/opencode/auth.json`; never read or print the token directly.
- Invocation: `ask_ai()` runs `opencode run --pure --agent jimbo --format json`.
- An injected OpenCode config gives the model no tools or filesystem access and
  uses the `minimal` model variant.
- Run from `/tmp/opencode` with project config and external skills disabled so
  Jimbo's prompt is not burdened with this repository's agent instructions.
- `--pure` disables external plugins, but OpenCode's built-in OpenAI auth plugin
  must remain enabled. Do not set `OPENCODE_DISABLE_DEFAULT_PLUGINS=1`; doing so
  breaks the authenticated provider.
- `opencode run --format json` emits JSON Lines events. `ask_ai()` collects text
  events and treats a nonzero exit or missing text as an error.

```python
text = ask_ai(prompt)
```

### History

Originally used a local Ollama model (`qwen2.5-32b-ctx32k` at `http://127.0.0.1:11434`).
This was switched to DeepSeek V4 Flash Free on 2026-07-26 because the local model
(28 GB) and the head-ful Factorio game client cannot fit in GPU memory simultaneously.
The hosted model is much faster (~15-25s per call vs 30-60s) and eliminates the
cold-start loading delay.

DeepSeek later exhausted its free quota and returned HTTP 429. Jimbo was switched
to OpenAI on 2026-07-26. Direct `gpt-4.1-mini` API access had no paid
quota, so the available lightweight OpenAI-provider equivalent,
`openai/gpt-5.4-mini`, is used instead.

### Prompt tuning on 2026-07-26

The step 1 classification prompt was tightened to default to SKIP unless the message
contains "Jimbo" — fixes the bot butting into player-to-player conversations.
The step 3 (no-RCON) prompt now instructs the model to vary its responses and
default to SKIP unless directly asked. Lines starting with `(Note:` or `(Corrected`
are stripped from replies before sending to prevent model meta-commentary leaking
into game chat. Returning players get a hardcoded "Welcome back, {player}!" instead
of an LLM call.

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
tail -f jimbo.log
```

To test JOIN greetings:
```bash
printf '%s [JOIN] TestPlayer joined the game\n' "$(date '+%Y-%m-%d %H:%M:%S')" >> /mnt/d/factorio-server/server-console.log
```

### Cold start caveat (archived — no longer relevant with hosted model)

The old local model (qwen2.5-32b-ctx32k, 28 GB) took 30-60 seconds to load into
GPU memory on first request after idle. Check if the model is loaded from the
Windows side:

```bash
ollama.exe ps
```

If the model isn't listed, expect the first response to take up to a minute.
Subsequent requests are faster but the model is still slow — budget ~20-45
seconds per LLM call. Do NOT queue multiple test messages rapidly; the model
will serialize them and the responses will be delayed and confusing.

### Model memory constraint (archived — no longer relevant with hosted model)

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

All three steps from IMPLEMENTATION.md are present in jimbo.py:
the chat listener, the AI decision loop, and the RCON query/send cycle.
They work end-to-end but can be rough around the edges — expect iterative
tuning rather than fundamental rewrites.

### Model self-knowledge prompts (2026-07-26)

All prompts that generate replies (step 1 classification, step 3 with/without RCON,
new player greeting) now include `"You run on the OpenAI GPT-5.4 Mini model via
OpenCode."` so the model can accurately answer questions about what
it is. Without this, the model hallucinates (e.g., "logistic-optimized neural net
architecture"). Don't add extra qualifiers like "not running on Ollama" — the model
will incorporate them into its persona description unprompted.

### `/version` RCON command (2026-07-26)

`/version` works as a direct RCON command — no `/silent-command` Lua needed.
Returns the Factorio version string (e.g., `2.1.12`). Added to the available
commands list and classification options alongside `/players`, `/evolution`, etc.
Do NOT try `game.product_version` or `game.build_version` — neither exists in
this server's version of the Lua API.

### Server owner (2026-07-26)

Jimbo now knows the server owner: all prompts include `"The server is owned
and operated by dlbattle."` Hardcoded since there's no game API to retrieve
this information.

### Version announcement on restart (2026-07-26)

On startup, the bot checks the current git commit hash against `last_commit.txt`.
If the hash changed, it runs `git log --oneline` between old and new commits,
asks the model to summarize the changes into a chat-friendly announcement, and
sends it in-game. The new hash is saved to `last_commit.txt` so the announcement
only fires once per update.

### Spontaneous comments (2026-07-26)

Every 10 minutes the bot checks whether it wants to make a spontaneous comment.
It's triggered both in the idle loop (when nobody's talking) and after processing
a message. The model sees log activity since its last successful spontaneous
comment, including chat and events, and can reply with a short message or SKIP.
Timer is rough — no async, no precision guarantee. The server owner can trigger
the same prompt immediately by saying `Jimbo, chime in`; this trigger is
restricted to username `dlbattle`.

### Deferred TODOs

- Catch `ValueError` as well as `OSError` when the Windows-hosted log invalidates
  a WSL file handle.
- Bound spontaneous-comment context if repeated SKIPs or API failures let it grow
  large enough to threaten the model context window.
- Clarify that `/time` reports elapsed server/game time, not wall-clock time, if
  this wording becomes bothersome.
- Add retry/backoff for transient AI API errors, especially HTTP 429 rate limits.

## Keep working
For clear, reversible tasks, act immediately after a brief plan; do not wait for "go ahead." Ask first only when requirements are ambiguous or an action is destructive.
