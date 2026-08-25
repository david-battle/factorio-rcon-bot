# Jimbo Operations Reference

Read this file when working on environment setup, RCON connectivity, AI provider
or model changes, local Ollama fallback, process management, testing, player-list
seeding, or one of the documented runtime pitfalls.

## Environment

- Bot code lives in WSL's native Linux filesystem (`~/factorio-rcon-bot`), not
  under `/mnt/c` or `/mnt/d`.
- The Factorio dedicated server runs natively on Windows at
  `D:\factorio-server`, started via `ss.bat`, and cannot be moved into WSL.
- Restart procedure: in the RCON console in the server's window run `/quit` to
  stop the server cleanly, then `:q` to exit the RCON console, then
  `D:\ss.bat` to relaunch.
- Automated restart from WSL: send `/quit` over RCON, reap the old console
  with `powershell.exe -Command "Stop-Process -Name rcon"`, launch
  `powershell.exe -Command "Start-Process -FilePath D:\ss.bat"` (opens a fresh
  console window), then verify the log reopened and RCON answers.
- The bot reaches RCON at `127.0.0.1:27015` across the WSL/Windows boundary.
- The server log is available to WSL at
  `/mnt/d/factorio-server/server-console.log`.
- Python dependencies use the shared `/mnt/d/.venv`, auto-activated by `.bashrc`.
- `unzip` is not installed on the WSL PATH. It is available at
  `~/.local/usr/bin/unzip`, installed without root via `apt-get download unzip`
  into `/tmp/opencode` and `dpkg -x` into `~/.local` (keep those pieces if the
  binary is ever lost). The 4.6 GB Factorio downloads are extracted with
  Windows `tar.exe` instead; `unzip` is only used for quick `-l`/`-t` checks.
- The standalone install under `/mnt/d/factorio-standalone/` was upgraded to
  Factorio `2.1.16` on 2026-08-24; `current` is a Windows junction to the
  version directory (see "Upgrade The Game Version" below). `/version` was
  rechecked on 2026-08-24 and reports `2.1.16`. Recheck `/version` before
  relying on version-sensitive runtime API behavior.

When the user says the "old repository," they mean
`/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints`. It contains historical
blueprint generators, tests, design notes, and an obsolete larger Jimbo project.
Read its `AGENTS.md` before consulting it, but treat this repository's current
instructions and operational findings as authoritative. Use old files as
evidence or source material rather than modifying or importing them wholesale.

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

Factorio supports concurrent RCON connections. The `Client` context manager
authenticates automatically, but a manually managed client must call
`client.connect(login=True)`. Calling `connect()` without `login=True` opens TCP
without authenticating, after which commands appear to hang until timeout.

The password is copied from the live server configuration into the gitignored
`rconpw`. Never hardcode, print, or commit it.

### Command Reference And Map Pings

See `docs/RCON_NOTES.md` for the command reference, the `[gps=x,y,surface]` map
ping format, and RCON/Lua facts. Jimbo's built-in platform and planet queries
are in `jimbo.py`; keep that executable implementation authoritative rather than
copying the Lua here.

### Logistic Availability Queries

Jimbo's structured availability decision is
`LOGISTICS|surface|item-name,item-name`. The surface and item fields use
lowercase internal names and are validated before Lua construction. The special
surface `all` means every surface with `LuaSurface.planet`; do not use
`LuaForce.logistic_networks` as a solar-system inventory because it previously
missed remote planetary networks.

On each surface, discover player networks through roboports and deduplicate them
by `LuaLogisticNetwork.network_id`. Keep disconnected networks separate. Locate
rocket silos with `find_entities_filtered()` and associate them through
`find_logistic_network_by_position()` so replies identify networks suitable for
shipping.

Use `LuaLogisticNetwork.get_contents()` for requested items. It returns
quality-aware entries with `name`, string `quality`, and `count`. Counts can be
negative when demand or reservations exceed stock. Sum `max(0, count)` across
qualities so player-facing availability is never negative. This number is stock,
not a recipe shortfall: compare it with exact recipe quantities retained in
dialogue. Zero available means the full required quantity is still needed.

Recipe prototypes are under `prototypes.recipe`, not the removed
`game.recipe_prototypes`. A bare planet list proves only which planets exist; it
does not establish material origins. Preserve the structured classifier examples,
input validation, deterministic tests, and failure acknowledgment when changing
this flow.

In Factorio 2.1, a recipe exposes plural `categories`; do not use the nonexistent
`LuaRecipePrototype.category`. Resolve compatible crafting entities with
`prototypes.get_entity_filtered()` and its `crafting-category` filter rather than
assuming that a recipe's product entity is its crafting machine.

## AI Provider

AI selection is centralized at the top of `jimbo.py`. Change only
`ai_profile_name` to switch the model and its associated provider. Keep
`ai_profiles`, its provider adapters, tests, and this reference synchronized; do
not duplicate model or provider choices elsewhere in application code.

Available profiles:

| Profile | Provider path | Model | Provider-specific setting |
| --- | --- | --- | --- |
| `free-models-router` | OpenAI-compatible OpenRouter API | `openrouter/free` | `https://openrouter.ai/api/v1`, ignored `openrouter.key` |
| `openai` | OpenCode CLI | `openai/gpt-5.4-mini` | OpenCode `openai` auth |
| `deepseek` | OpenAI-compatible OpenCode API | `deepseek-v4-flash` | `https://opencode.ai/zen/v1`, OpenCode `opencode` auth |
| `big-pickle` | OpenAI-compatible OpenCode API | `big-pickle` | `https://opencode.ai/zen/v1`, OpenCode `opencode` auth |
| `nemotron` | OpenAI-compatible OpenRouter API | `nvidia/nemotron-3-ultra-550b-a55b:free` | `https://openrouter.ai/api/v1`, ignored `openrouter.key` |
| `ollama` | Local Ollama | `qwen2.5-32b-ctx32k` | `http://127.0.0.1:11434` |

The current profile is `deepseek`. It uses the OpenAI-compatible adapter
against `https://opencode.ai/zen/v1` (OpenCode Zen), reading the `opencode`
credential from `~/.local/share/opencode/auth.json`; never read or print a
token. It runs the paid DeepSeek V4 Flash so replies do not stop when free
quota is exhausted. The model behaves as a reasoning model and reports its
reasoning in `usage.reasoning_tokens` rather than leaking it into
`message.content`, so no reasoning-exclusion extra body is needed (unlike
OpenRouter's Nemotron, which required
`extra_body: {"reasoning": {"exclude": True}}`). The `big-pickle` profile uses
the same Zen endpoint and credential; Big Pickle allows up to 4096 completion
tokens. The `free-models-router` profile instead uses the OpenAI-compatible
adapter against `https://openrouter.ai/api/v1` (OpenRouter), reading
`openrouter.key`; never read or print a key. The router picks a free model
automatically; that profile limits replies to 256 completion tokens and
requests low reasoning effort with reasoning excluded from the response. The `openai` profile instead
launches an isolated, tool-denied `opencode run --pure --agent jimbo --format
json` from `/tmp/opencode`, with project configuration and external skills
disabled. The built-in OpenAI auth plugin must remain enabled, so do not set
`OPENCODE_DISABLE_DEFAULT_PLUGINS=1`. Transient timeouts, rate limits, and common
HTTP 5xx failures get three total attempts; permanent failures fail immediately.
Model identity is derived from the selected profile.

### OpenCode CLI Containment

OpenCode is only the `openai` profile's model/authentication adapter. It
does not make Jimbo a coding agent: the invocation is pure, project configuration
is disabled, and every tool permission is denied. The other adapters call their
provider directly; DeepSeek reads an OpenCode credential but does not launch the
OpenCode executable.

OpenCode 1.18.9 was observed extracting a 5,576,816-byte Rust FFF
(`libfff_c`) search library to a uniquely named hidden `/tmp/.*.so` file on model
calls without removing it. File timestamps matched Jimbo's scheduled and direct
model calls; about 1,410 stale copies consumed roughly 7.9 GB. Zero-byte hidden
`.node` extraction placeholders were also observed but did not consume material
space.

`ask_opencode()` therefore gives every invocation a private `TMPDIR` managed by
`tempfile.TemporaryDirectory`. OpenCode may load native files there while it is
running, and Python removes the directory after the subprocess exits or raises.
Keep deterministic cleanup coverage when changing this adapter. Do not add a
broad `/tmp` cleanup job or delete matching files while an OpenCode process may
still be using them.

OpenCode is not architecturally required. A future explicit provider change may
replace this adapter with the official OpenAI Python client, avoiding a large
subprocess launch and native extraction on every model call. Do that only when
the owner supplies a suitable OpenAI API credential and accepts its API billing;
do not assume the current OpenCode login can be reused directly. Preserve central
profile selection, retry behavior, tool isolation expectations, tests, and this
reference during such a migration. Until then, the contained OpenCode adapter is
the smallest working path.

### Model Call Latency Findings

Measured on 2026-08-23 against OpenCode Zen (`deepseek-v4-flash`): the first
model call of a process pays a one-time penalty of roughly 7–19 seconds
regardless of prompt size; later calls run ~1–5 seconds even after minutes of
idle, reusing one OpenAI client does not help, and capping completion tokens
does not help either (reasoning tokens count against such caps, risking
truncated replies). Jimbo makes no model call during startup, so
`warm_up_ai()` fires a throwaway call right after the online announcement to
absorb the penalty while nobody is waiting. `ask_ai` logs each call duration
to `jimbo.log`; check those timings before chasing perceived slowness.

### Provider History

Jimbo began on local Ollama, moved to hosted DeepSeek because the local model
competed with the Factorio client for GPU memory, and moved to OpenAI after the
free DeepSeek quota was exhausted. It later moved through Groq, Nemotron 3 Ultra
via OpenRouter, DeepSeek V4 Flash via OpenCode Zen, Big Pickle via OpenCode Zen,
Free Models Router via OpenRouter, and now runs on the paid DeepSeek V4 Flash
via OpenCode Zen after the owner added OpenCode credit. The predefined profiles
retain these working paths for manual selection; there is no automatic fallback.

### Groq

The `groq` profile is no longer defined in `jimbo.py`. Historically it used
`openai/gpt-oss-120b` through the OpenAI-compatible adapter with gitignored
`groq-api-key.txt`, limited replies to 256 tokens, requested low reasoning effort,
and excluded reasoning from the response. Rate and account quotas were its main
operational risk. If re-adding this profile, keep `groq-api-key.txt` gitignored
and restore those settings.

### Local Ollama (manual alternative)

Ollama is retained as a manually-selected alternative provider only; it is NOT a
dynamic/automatic fallback. To use it, set `ai_profile_name = "ollama"` in
`jimbo.py`'s top config block. There is no automatic provider fallback in code.
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
nohup setsid python -u program.py </dev/null >program.log 2>&1 & echo $! >program.pid
```

The separate session matters when launching through a development command
runner: a plain `nohup` Jimbo process was reaped when its launcher exited, while
the `setsid` launch survived. Verify the recorded PID from a separate command
session with `ps`; do not rely only on a check performed before the launching
shell exits. Use `print(..., flush=True)` in long-running or redirected Python
processes.

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

Factorio saves back to the file passed to `--start-server`, including when the
last player disconnects and on clean shutdown. Use these roles consistently:

- `/mnt/d/factorio-server/saves/New Space Age Server.zip` is the mutable live
  save from which the server starts.
- `/mnt/d/factorio-server/saves/_autosaveN.zip` files are Factorio's rotating
  short-term recovery saves.
- Timestamped files under `/mnt/d/factorio-server/saves/archive/` are immutable
  manual checkpoints.

Do not use `server-save <filename>`: it resolves under Factorio's write-data
directory, and a failed save terminates the multiplayer server.

### Quick Backup Copy

A routine request to "make a backup" means ask the server to flush its save
first, then copy the live save into the archive with a timestamped name, leaving
the live file untouched and the server running:

1. Run `/server-save` through the verified RCON connection and require success
   (this also makes the live save match the in-game world). Do not skip this
   step even if the server appears idle.
2. Copy the live save:

```bash
cp "/mnt/d/factorio-server/saves/New Space Age Server.zip" \
   "/mnt/d/factorio-server/saves/archive/New Space Age Server backup $(date +%Y-%m-%d_%H-%M-%S).zip"
```

3. Verify the copy exists, is nonempty, and matches the live file's size, then
   report its exact path. This is a snapshot of the save as currently written to
   disk; it is not a checkpoint. For the guaranteed-safe-then-restorable
   checkpoint procedure, use the next section.

### Overnight Backup Loop

`backup_loop.py` repeats the Quick Backup Copy steps every 15 minutes and keeps
every archive file, for overnight unattended coverage. Launch detached with the
standard pattern, then confirm the recorded PID from a separate session:

```bash
nohup setsid python -u backup_loop.py </dev/null >backup_loop.log 2>&1 & echo $! >backup_loop.pid
```

It saves immediately on launch, then every 15 minutes. Stop it with
`kill "$(cat backup_loop.pid)"`. A `/server-save` or copy failure is logged to
`backup_loop.log` and the loop keeps trying next interval; it never overwrites an
existing archive file.

### Create A Checkpoint

When asked to create a checkpoint:

1. Run `/server-save` through the verified RCON connection and require success.
2. Create the archive directory if needed, then copy the live save to
   `checkpoint-YYYY-MM-DD_HH-mm-ss.zip`. Never overwrite an existing checkpoint.
3. Verify that it exists, is nonempty, and is a readable ZIP; report its exact
   path. Do not restart services or expose the RCON password. If saving fails, do
   not copy or claim a checkpoint.

### Restore The Last Checkpoint

Restoring replaces the live world and disconnects players. Obtain explicit
confirmation immediately before stopping the server, then:

1. Select the lexicographically last `archive/checkpoint-*.zip`; exclude autosaves
   and `pre-restore-*`, and validate the selected ZIP before stopping anything.
2. Stop Factorio cleanly with its existing Windows procedure and verify exit. Its
   final save may overwrite the live file; do not kill it while it writes.
3. Preserve the final live file as
   `archive/pre-restore-YYYY-MM-DD_HH-mm-ss.zip` for emergency recovery.
4. Copy the checkpoint to a temporary save-directory file, validate it, then
   replace `New Space Age Server.zip`; leave the archive unchanged.
5. Start Factorio normally. Confirm in
   `/mnt/d/factorio-standalone/current/factorio-current.log` that it loaded
   the expected save, then verify RCON. Restart Jimbo only if reconnection keeps
   failing after Factorio is available.

Stop and ask if no checkpoint exists, validation fails, stop/start is unclear, or
the live save changes unexpectedly. Report both archive paths and verification.

### Start A New Game

Starting fresh replaces the live world; preserve the old save first. Obtain
explicit confirmation before stopping the server, then:

1. Stop Factorio cleanly with its existing Windows procedure and verify exit. Its
   final save updates the live file.
2. Move the live save `New Space Age Server.zip` to
   `archive/pre-newgame-YYYY-MM-DD_HH-mm-ss.zip`. Never overwrite an existing
   archive file. Verify nothing remains at the live path.
3. Run `D:\ss.bat`; its `if not exist` guard generates a fresh world at the live
   path.
4. Reseed `known_players.txt` from `/players` (see the seeding section); the old
   roster no longer applies to a fresh world.
5. Verify the new save exists, the log reopened, and RCON answers.

### Upgrade The Game Version

Each Factorio zip extracts to a version-named folder (e.g.
`Factorio_2.1.16/`). The dedicated server always launches from
`D:\factorio-standalone\current`, so an upgrade repoints that junction; all
server data stays in `D:\factorio-server`. The server must be stopped.
Downloads land in `/mnt/c/Users/dlbat/Downloads/` as
`factorio-space-age_win_<version>.zip`; while a browser is still downloading,
the file is a growing `Unconfirmed <id>.crdownload` and must not be touched.

1. Verify the zip's integrity and root folder with `~/.local/usr/bin/unzip -l`
   and `-t` (the binary is not on PATH; see Environment).
2. Extract it into `/mnt/d/factorio-standalone/` (use Windows
   `/mnt/c/Windows/System32/tar.exe -xf <zip> -C D:\factorio-standalone` from
   WSL: it runs natively and is far faster than `unzip` over the 9P mounts).
   Do not use WSL `unzip` for extraction: a 5.3 GB zip was still only ~60%
   done after ten minutes, and its kill left a partial tree that had to be
   overwritten.
3. Confirm `bin/x64/factorio.exe` exists and `data/base/info.json` reports the
   expected version; compare the file count against `unzip -l` (20,833 files
   for 2.1.16).
4. Confirm no `factorio.exe` is running, then replace the junction:
   `cmd.exe /c "mklink /J D:\factorio-standalone\current D:\factorio-standalone\<version>"`.
   (`current` is a Windows junction, not a WSL symlink; `mklink /J` needs no
   admin. Delete the old junction first with `rm` from WSL.)
5. Verify `cmd /c dir /a D:\factorio-standalone` shows the junction and that
   `current/bin/x64/factorio.exe` resolves.
6. Keep the immediate previous version directory in place as rollback; after
   the new version is confirmed running (step 8), remove older trees, redundant
   zips, and empty extraction debris (e.g. `_extract_temp`). The running server
   is never affected: it launches only through `current`.
7. On first run the new install dir generates its own write-data (`config/`,
   `temp/`, `player-data.json`, `factorio-current.log`) because its
   `config-path.cfg` sets `use-system-read-write-data-directories=false`;
   nothing needs carrying over from the old version dir. All real server data
   comes from `D:\factorio-server`.
8. Restart via `D:\ss.bat` and recheck `/version`; update the version reference
   at the top of this file.
9. Regenerate the model-facing scripting reference from the new install with
   `python generate_lua_reference.py` (reads
   `doc-html/runtime-api.json` under `current`), then restart Jimbo so he
   loads it. Commit the updated `lua_essentials.txt`; never commit the source
   JSON.

## Runtime Pitfalls

### Server Pauses With No Players Online

The dedicated server intentionally pauses its simulation when no player is
connected. With zero players online, expect: game time frozen, no autosaves, a
log that records only RCON connections and join attempts, and `game.tick`
advancing by roughly one tick per ten seconds. This is normal idle behavior,
not a hang or a performance problem. A `[JOIN]` resumes the simulation. When
checking whether the server is down, rely on whether RCON responds and whether
the world resumes when a player connects; do not treat frozen time or missing
autosaves as evidence of a fault.

### Production Cell Search Traces

Each completed production-cell Phase 1 search writes one
`PRODUCE search trace:` line to `jimbo.log`. The trace reports the resolved
surface and origin, direction, compatible machines, anchors examined,
structurally valid layouts, occupancy and exact-placement rejections, support
misses for heat/logistics/construction/power, and the selected strict or fallback
anchor. Compact and standard layouts can both be evaluated at one anchor, so
their outcome counters may exceed the anchor count.

The trace is stripped before reply composition. Use it to diagnose why an
apparently valid site was missed without replaying Phase 2. A missing trace means
the request never completed Phase 1—for example, classification skipped or
failed, the player/surface/recipe was rejected before search, or RCON failed.
Never infer that a mutation occurred from a trace; only the separate verified
Phase 2 `PRODUCE response` establishes placement.

### Opaque Chat Item Links

The server log records a linked blueprint as an opaque token such as
`[special-item=internal_12]`, without its exchange string or contents. The
numeric suffix is not `LuaItemCommon.item_number`. Treat it as opaque; scanning
a player's inventory is useful only when the intended item is otherwise
unambiguous. If several candidates exist, ask the player to hold, isolate, or
export the item rather than guessing.

### Remote View Player Inventories

On Factorio 2.1.12, `LuaPlayer.get_main_inventory()` returned `nil` for an online
player in remote view (controller type 7), although `LuaPlayer.character` and
the character's main inventory remained valid. For physical item inspection or
delivery, validate the character and use `player.character.get_main_inventory()`;
still handle players without a physical character deterministically. Do not
interpret a missing current-controller inventory as proof that the player is
offline.

### Cross-filesystem Handle Invalidation

Windows writes to the server log can invalidate WSL's open file descriptor.
Operations such as `f.tell()` may raise `ValueError: I/O operation on closed
file`. Jimbo catches both `OSError` and `ValueError` and reopens the file.

### RCON Multi-line Messages

Jimbo sends each filtered chat reply line separately through
`send_jimbo_lines()` (one `Jimbo says <line>` command per line). RCON responses
keep embedded newlines, but keep any single response under ~4 KB (see
`docs/RCON_NOTES.md`).

### Platform Names

Platform-name markup cleanup and complete-list behavior are encoded in Jimbo's
reply prompts; keep the executable implementation authoritative.

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
