# Jimbo Operations Reference

Read this file when working on environment setup, RCON connectivity, AI provider
or model changes, local Ollama fallback, process management, testing, player-list
seeding, or one of the documented runtime pitfalls.

## Environment

- Bot code lives in WSL's native Linux filesystem (`~/factorio-rcon-bot`), not
  under `/mnt/c` or `/mnt/d`.
- The Factorio dedicated server runs natively on Windows at
  `D:\factorio-server`, started via `ss.bat`, and cannot be moved into WSL.
- The bot reaches RCON at `127.0.0.1:27015` across the WSL/Windows boundary.
- The server log is available to WSL at
  `/mnt/d/factorio-server/server-console.log`.
- Python dependencies use the shared `/mnt/d/.venv`, auto-activated by `.bashrc`.

## RCON Connection

Use the `rcon` package's `rcon.source` module. This exact library and connection
were verified; do not substitute `mcrcon` or another library.

```python
from rcon.source import Client

with open("rconpw") as f:
    password = f.read().strip()

with Client("127.0.0.1", 27015, passwd=password) as client:
    response = client.run("/players")
    print(response)
```

The password is copied from the live server configuration into the gitignored
`rconpw`. Never hardcode, print, or commit it.

## AI Provider

AI selection is centralized at the top of `jimbo.py`. Change only
`ai_profile_name` to switch the model and its associated provider. Keep
`ai_profiles`, its provider adapters, tests, and this reference synchronized; do
not duplicate model or provider choices elsewhere in application code.

Available profiles:

| Profile | Provider path | Model | Provider-specific setting |
| --- | --- | --- | --- |
| `openai` | OpenCode CLI | `openai/gpt-5.4-mini` | OpenCode `openai` auth |
| `deepseek` | OpenAI-compatible OpenCode API | `deepseek-v4-flash-free` | `https://opencode.ai/zen/v1`, OpenCode `opencode` auth |
| `ollama` | Local Ollama | `qwen2.5-32b-ctx32k` | `http://127.0.0.1:11434` |

The current profile is `openai`:

- Model: `openai/gpt-5.4-mini`
- Auth: OpenCode's configured `openai` provider in
  `~/.local/share/opencode/auth.json`; never read or print the token directly.
- Invocation: `ask_ai()` runs
  `opencode run --pure --agent jimbo --format json`.
- An injected OpenCode config denies tools and filesystem access and uses the
  `minimal` model variant.
- The command runs from `/tmp/opencode` with project config and external skills
  disabled so Jimbo does not receive this repository's agent instructions.
- `--pure` disables external plugins, but OpenCode's built-in OpenAI auth plugin
  must remain enabled. Do not set `OPENCODE_DISABLE_DEFAULT_PLUGINS=1`.
- JSON Lines text events are collected as the response. A nonzero exit or no
  text is treated as an error.
- Transient timeouts, rate limits, and common HTTP 5xx failures get up to three
  total attempts with 2-second and 4-second backoff. Permanent failures fail on
  the first attempt.
- Reply prompts derive model identity from the selected profile.

### Provider History

Jimbo originally used local Ollama model `qwen2.5-32b-ctx32k` at
`http://127.0.0.1:11434`. It moved to DeepSeek V4 Flash Free on 2026-07-26
because the 28 GB local model and headful Factorio client cannot fit in GPU
memory simultaneously. Hosted inference was also faster, around 15-25 seconds
instead of 30-60 seconds.

DeepSeek later exhausted its free quota with HTTP 429 responses. Direct
`gpt-4.1-mini` API access had no paid quota, so Jimbo moved to the available
OpenCode OpenAI-provider equivalent, `openai/gpt-5.4-mini`, on 2026-07-26.

### Local Ollama Fallback

The old local model can take 30-60 seconds to load after idle. Check it from the
Windows side with:

```bash
ollama.exe ps
```

If it is not listed, expect a slow first response. Later calls still take about
20-45 seconds. Do not queue test messages rapidly because inference serializes.

The headful Factorio game client and 28 GB local model do not fit in memory at
the same time. The Windows dedicated server and WSL Ollama can coexist because
they run in separate OS instances.

For weaker local coding models only: if one creates an unparseable Python file
and cannot repair whitespace reliably with Edit, replace the complete enclosing
function or file with Write, then run `python -m py_compile`.

## Process Management

Long-running monitors must be detached with all streams redirected and their PID
saved:

```bash
nohup python -u program.py </dev/null >program.log 2>&1 & echo $! >program.pid
```

Verify the PID with `ps`; do not wait for the process to exit. Use
`print(..., flush=True)` in long-running or redirected Python processes.

## Offline Testing

No player needs to enter the game. Append simulated activity to the server log:

```bash
printf '%s [CHAT] dlbattle: Jimbo what is the evolution factor?\n' "$(date '+%Y-%m-%d %H:%M:%S')" >> /mnt/d/factorio-server/server-console.log
```

Watch `jimbo.log` for processing and the live server log for the RCON response.
Test joins similarly:

```bash
printf '%s [JOIN] TestPlayer joined the game\n' "$(date '+%Y-%m-%d %H:%M:%S')" >> /mnt/d/factorio-server/server-console.log
```

## Save Checkpoints

Factorio's dedicated server treats the file passed to `--start-server` as a
mutable live save. In addition to rotating `_autosaveN.zip` files, it saves back
to the loaded file when the last player disconnects and on a clean shutdown.
Therefore, do not treat `New Space Age Server.zip` as a durable restore point.

Use these roles consistently:

- `/mnt/d/factorio-server/saves/New Space Age Server.zip` is the mutable live
  save from which the server starts.
- `/mnt/d/factorio-server/saves/_autosaveN.zip` files are Factorio's rotating
  short-term recovery saves.
- Timestamped files under `/mnt/d/factorio-server/saves/archive/` are immutable
  manual checkpoints.

Do not use `server-save <filename>` to create a checkpoint. A relative name is
resolved under the Factorio installation's write-data directory rather than
beside the loaded save, and a failed save terminates the multiplayer server.

### Create A Checkpoint

When asked to create a checkpoint:

1. Use the verified `rcon.source.Client` connection described above to run
   `/server-save`. Wait for the RCON call to complete successfully. This first
   makes the mutable live save current.
2. Create the archive directory if it does not exist.
3. Copy the live save to an archive filename in the form
   `checkpoint-YYYY-MM-DD_HH-mm-ss.zip`. Never overwrite an existing checkpoint.
4. Verify that the checkpoint exists, is nonempty, and is a readable ZIP file.
5. Report the exact checkpoint path. Do not restart Factorio or Jimbo.

The copy, directory creation, and ZIP validation can be performed from WSL. Do
not print the RCON password. If `/server-save` fails, do not copy the live file
and do not claim that a checkpoint was created.

### Restore The Last Checkpoint

Restoring replaces the current live world and disconnects players. Treat it as
destructive and obtain explicit confirmation immediately before stopping the
server. Then:

1. Select the lexicographically last file matching
   `/mnt/d/factorio-server/saves/archive/checkpoint-*.zip`. With the timestamp
   format above, this is the newest checkpoint. Do not select an `_autosaveN.zip`
   or a `pre-restore-*.zip` file.
2. Validate that the selected checkpoint is a readable, nonempty ZIP before
   stopping anything.
3. Stop Factorio cleanly using the server's existing Windows process-management
   procedure and verify that the process exited. Do not kill it while it is
   writing a save. Its final save may overwrite the live file; that is expected.
4. Preserve that final live file as
   `archive/pre-restore-YYYY-MM-DD_HH-mm-ss.zip` for emergency recovery.
5. Copy the selected checkpoint to a temporary file in
   `/mnt/d/factorio-server/saves/`, validate the temporary ZIP, then replace
   `New Space Age Server.zip` with it. Keep the selected archive checkpoint
   unchanged.
6. Start Factorio with the normal server launcher. Confirm in
   `/mnt/d/factorio-standalone/current/factorio-current.log` that it loaded
   `D:\factorio-server\saves\New Space Age Server.zip` successfully, then verify
   that RCON is available.
7. Jimbo should reconnect automatically. Restart Jimbo only if its log shows
   that reconnection continues to fail after Factorio is available.

If no matching checkpoint exists, validation fails, the server's stop/start
procedure is unclear, or the live save changes unexpectedly during restoration,
stop and ask rather than guessing. Report the checkpoint restored, the emergency
pre-restore copy, and the verification result.

## Runtime Pitfalls

### Cross-filesystem Handle Invalidation

Windows writes to the server log can invalidate WSL's open file descriptor.
Operations such as `f.tell()` may raise `ValueError: I/O operation on closed
file`. Jimbo catches both `OSError` and `ValueError` and reopens the file.

### RCON Multi-line Messages

RCON only delivers the first line of a multi-line chat command. Send each line
separately:

```python
for line in reply.split("\n"):
    if line.strip():
        client.run(f"Jimbo says {line.strip()}")
```

### Platform Names

Platform names may contain cargo descriptions and signal markup such as
`[item=space-science-pack]` or
`[planet=nauvis][planet=vulcanus]Sausage`. Reply generation must strip
`[item=...]`, `[planet=...]`, `[virtual-signal=...]`, and
`[space-location=...]` brackets while retaining surrounding text. When a list is
requested, include every RCON response line without inventing names.

## known_players.txt Seeding

Seed this gitignored file once from `/players`. Jimbo appends players as they
join. Reseed only after replacing/resetting the save, losing the file, or
clearing test/debris entries:

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
