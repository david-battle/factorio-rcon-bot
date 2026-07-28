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

### Command Reference

- `/players`: all players who have played this save.
- `/players online`: currently connected players.
- `/evolution`: enemy evolution factor.
- `/time`: elapsed server/game time, not wall-clock time.
- `/version`: Factorio version. Do not use nonexistent Lua properties
  `game.product_version` or `game.build_version`.
- Plain Lua often returns nothing; use `rcon.print()` inside `/silent-command`.
- Raw RCON text without a slash appears in chat as `<server>`.

Canned platform query:

```text
/silent-command local list={};for _,surface in pairs(game.surfaces) do if surface.platform then table.insert(list,surface.platform.name) end end;rcon.print(table.concat(list,"\n"))
```

Canned planet query:

```text
/silent-command local list={};for _,surface in pairs(game.surfaces) do if surface.planet then table.insert(list, surface.planet.name:sub(1,1):upper()..surface.planet.name:sub(2)) end end;rcon.print(table.concat(list,"\n"))
```

### Map Pings

Factorio chat recognizes `[gps=x,y,surface]` as a clickable map location. Send it
as raw RCON chat, including Jimbo's normal prefix:

```text
Jimbo says Auto-research control lab: [gps=-1.5,-57.5,nauvis]
```

Use the player's requested coordinates and surface rather than assuming Nauvis.

### Entity Ghost Inspection And Cloning

A live test on 2026-07-28 confirmed that Jimbo can inspect and reproduce an
entity ghost without reconstructing its settings manually. For a GPS-directed
inspection, resolve the supplied surface or use the requesting player's current
surface, then search nearby `entity-ghost` entities and report `ghost_name`,
`ghost_type`, position, force, quality, unit number, and
`is_registered_for_construction()`.

Equipment and inventory requests on a vehicle ghost are not represented by its
runtime `grid`, which can be empty. Read both of these properties instead:

- `item_requests` is the read-only item/count summary.
- `insert_plan` is the exact writable blueprint plan, including inventory slot
  destinations and equipment-grid counts.

The tested tank ghost requested two nuclear fuel in inventory slots 0 and 1,
one portable fission reactor, two Battery MK2s, three exoskeletons, and one
energy shield. `LuaEntity.clone{position=..., surface=..., force=...}` preserved
its ghost prototype, direction, quality, `item_requests`, and complete
`insert_plan`.

A future Jimbo action should use this sequence:

1. Require a current explicit request and locate the source ghost read-only.
2. Verify the requesting player is online and resolve their live surface and
   position.
3. Use `find_non_colliding_position_in_box()` to constrain the destination to
   the requested direction, such as a rectangle north of the player.
4. Snapshot the source `item_requests` and `insert_plan`, then clone once. Treat
   cloning as unsafe to replay automatically after an RCON disconnect.
5. Compare the clone's prototype, direction, quality, requests, and insert plan
   to the source. Destroy only the new clone if validation fails.
6. Print the actual result through RCON and send the verified clone position as
   a clickable GPS link.

Construction robots may fulfill the new ghost immediately if the network has
the requested items, so verification should happen in the same Lua command as
the clone. Never destroy or alter the source ghost.

### Logistic Production Cells

A reusable production cell consists of one crafting machine, a requester chest
feeding it through an input inserter, and an output inserter feeding a passive
provider chest. A bulk input inserter handles recipes with large ingredient
stacks; a regular output inserter is sufficient for most single-product recipes,
although cloning an existing cell should preserve its inserter choices.

The tested compact layout placed both inserters immediately beside the machine
and both chests one tile beyond them. When reproducing it, validate the complete
machine footprint plus both inserter and chest positions, and confirm the
requester remains inside a logistic network.

For an assembler centered at `(x, y)`, the verified south-side layout is:

- Bulk input inserter at `(x, y+2)` and requester chest at `(x, y+3)`.
- Regular output inserter at `(x-1, y+2)` and passive provider chest at
  `(x-1, y+3)`.

Adjacent Assembling Machine 3 cells can use centers three tiles apart
horizontally. An expanded area search may then return the neighboring assembler
because its bounding box touches the search area even though placement is valid.
Use exact planned positions plus `can_place_entity()` for collision checks, and
inspect the actual new footprint for belts and other infrastructure rather than
blindly rejecting a known adjacent cell.

Do not rely on `can_place_entity(..., build_check_type=script_ghost)` alone to
protect existing infrastructure: live testing showed that it can accept a ghost
plan overlapping belts. Before creating anything, scan the complete destination
bounding box for existing entities and ghosts, especially belts, underground
belts, splitters, pipes, and wiring components. Treat any unplanned occupancy as
blocked and choose another location.

After setting the new machine ghost's recipe, this call reproduces the player's
shift-right-click/shift-left-click recipe paste onto the requester ghost:

```text
requester_ghost.copy_settings(assembler_ghost, player)
```

This lets Factorio calculate request buffers rather than requiring Jimbo to
guess ingredient quantities. For an Assembling Machine 3 making
`exoskeleton-equipment`, the verified requests were 75 steel plates, 37
processing units, and 112 electric engine units. Validate that every recipe
ingredient appears with a positive request before accepting the new cell, and
remove all newly created ghosts if any placement or settings check fails.

Verified recipe IDs and generated requester buffers:

| Product | Recipe ID | Requests |
| --- | --- | --- |
| Energy shield | `energy-shield-equipment` | 37 steel plates, 18 advanced circuits |
| Personal battery MK1 | `battery-equipment` | 37 steel plates, 18 batteries |
| Personal battery MK2 | `battery-mk2-equipment` | 56 processing units, 18 low-density structures, 37 Battery MK1s |
| Personal battery MK3 | `battery-mk3-equipment` | 37 supercapacitors, 18 Battery MK2s |
| Power Armor MK2 | `power-armor-mk2` | 60 processing units, 40 electric engine units, 30 low-density structures, 100 speed modules, 100 efficiency modules |

The verified operation order is important: locate each source with
`surface.find_entity(name, position)` and confirm its unit number, create and
`copy_settings()` to all five ghosts, change the assembler recipe, then copy
settings from that assembler ghost to the requester ghost. Cached unit numbers
alone are not sufficient source locators because players may rebuild entities.

When the player preplaces an empty assembler to specify exact alignment, preserve
that real entity. Verify it has no recipe and is powered, set its requested
recipe, and create only the four peripheral ghosts. On failure, clear only the
new recipe and remove only the newly created ghosts; never destroy the player's
assembler.

Wrap multi-entity creation and configuration in one `pcall`; retain references
to every new ghost and destroy only those new ghosts on any failure. Check
`is_registered_for_construction()` in that same command. A later read may report
different queue registration after robots claim work while the ghost itself is
still present, so verify continued existence separately by exact position and
`ghost_name`.

Power must be validated separately from placement and logistic coverage. Before
creating a cell, locate a real electric pole, verify `pole.electric_network` is
not `nil`, read its quality-aware supply radius with
`pole.prototype.get_supply_area_distance(pole.quality)`, and place the assembler
inside that area. Also verify the requester with
`surface.find_logistic_network_by_position()`.

If the requested compact destination lacks coverage, extending power is standard
practice instead of creating an unpowered cell or immediately moving it. Treat
the extension as a separately validated subplan in the same `pcall`: choose the
smallest adequate pole at a collision-free position in construction coverage,
verify its quality-aware supply area covers the assembler, and connect its copper
wire connector to a live pole whose electric network is not `nil`. Require
`can_wire_reach()` and verify `connect_to()` or `is_connected_to()` using
`defines.wire_connector_id.pole_copper`; include the new pole ghost in rollback.
Once built, `assembler.is_connected_to_electric_network()` is the definitive
check that its network has a power producer.

In the verified close-spacing test, the Power Armor MK2 assembler at
`(-0.5, -15.5)` was half a tile beyond the existing substation's supply area. A
substation ghost at `(-5, -9)`, explicitly wired to the connected substation at
`(9, -9)`, covered the assembler while preserving three-tile cell spacing.

### Automatic Research Control

The current save's circuit-driven research is controlled by the `set_research`
option on one lab. As discovered on 2026-07-28, that lab was unit `985803` at
`[-1.5, -57.5]` on Nauvis. Its unit number and location may change if players
rebuild it, so discover the active control lab before changing anything:

```text
/silent-command local s=game.surfaces["nauvis"];local out={};for _,e in pairs(s.find_entities_filtered{type="lab",force="player"}) do local cb=e.get_control_behavior();if cb and cb.set_research then out[#out+1]=string.format("unit=%s pos=%.1f,%.1f",e.unit_number,e.position.x,e.position.y) end end;rcon.print(#out>0 and table.concat(out,";") or "(none)")
```

After verifying the entity's unit number and position, set only
`e.get_control_behavior().set_research` to `false` to disable automation or
`true` to re-enable it. Verify the value afterward with RCON. This preserves the
lab, combinators, wiring, research conditions, current technology, and research
queue, making it the least destructive and most reversible control. Do not clear
the queue or dismantle circuitry merely to pause automatic selection.

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
| `groq` | OpenAI-compatible Groq API | `openai/gpt-oss-120b` | `https://api.groq.com/openai/v1`, ignored `groq-api-key.txt` |
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

### Gemini and Google Antigravity

The earlier repository at
`/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints/jimbo-local-bot`
contains direct chat-log evidence that Google Antigravity with Gemini was used
briefly to continue Jimbo development on 2026-07-22. The owner reported running
out of free quota within ten minutes and later said Gemini had been used "for a
while." This indicates development use through Antigravity, not Gemini through
OpenCode; no surviving OpenCode configuration or session metadata selects a
Gemini development model.

That repository also implemented `gemini-2.5-flash` as a bot-provider fallback
in commit `5b79129`, selected when OpenCode authentication was unavailable and a
local `gemini-api-key.txt` existed. The retained runtime records identify Qwen,
Groq, OpenCode Zen, and Mistral runs, but no Gemini startup or response. Treat an
actual Gemini-powered Jimbo run as unproven rather than claiming it occurred.

Antigravity quota exhaustion is normally temporary. As checked against Google's
Antigravity plans documentation on 2026-07-27, baseline quota for accounts
without Google AI Pro or Ultra refreshes weekly; paid-plan baseline quota
refreshes every five hours until its weekly limit is reached. Current status and
remaining model quota can be refreshed in Antigravity CLI with `/usage` or
`/quota`. Limits may change, so consult `https://antigravity.google/docs/plans`
before relying on the recorded schedule.

### Groq

The optional `groq` profile uses `openai/gpt-oss-120b`. It reuses the
OpenAI-compatible adapter with a dedicated key in gitignored
`groq-api-key.txt`, a 256-token completion limit, low reasoning effort, and
reasoning excluded from the response.

The archived bot recorded 167 successful responses from this model, and both
its proof of concept and full bot used it live. It was dropped after rate-limit
and quota exhaustion, not an integration failure. A console-only check on
2026-07-27 confirmed that the current credential and model returned the exact
requested text in 9.06 seconds. Account limits remain the main operational risk
because Jimbo normally makes two model calls per handled chat request.

Mistral was investigated but is not a configured profile. Its archived and
OpenCode credentials both returned HTTP 401 in manual checks, and the owner
prefers DeepSeek rather than another model accessed through OpenCode.

Official Groq references:

- Model: `https://console.groq.com/docs/model/openai/gpt-oss-120b`
- OpenAI compatibility: `https://console.groq.com/docs/openai`
- Reasoning behavior: `https://console.groq.com/docs/reasoning`

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
