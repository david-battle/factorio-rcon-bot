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

### Command Reference

- `/players`: all players who have played this save.
- `/players online`: currently connected players.
- `/evolution`: enemy evolution factor.
- `/time`: elapsed server/game time, not wall-clock time.
- `/version`: Factorio version. Do not use nonexistent Lua properties
  `game.product_version` or `game.build_version`.
- Plain Lua often returns nothing; use `rcon.print()` inside `/silent-command`.
- Raw RCON text without a slash appears in chat as `<server>`.
- Jimbo's built-in platform and planet queries are in `jimbo.py`; keep that
  executable implementation authoritative rather than copying the Lua here.

### Map Pings

Factorio chat recognizes `[gps=x,y,surface]` as a clickable map location. Send it
as raw RCON chat, including Jimbo's normal prefix:

```text
Jimbo says Requested location: [gps=128,64,nauvis]
```

Use the player's requested coordinates and surface rather than assuming Nauvis.
Factorio world chunks are 32 x 32 tiles, with boundaries and corners at
coordinates divisible by 32.

### Exact Blueprint Deployment

For precise remote deployment, do not call `LuaItemStack.build_blueprint()`
directly on the live surface: its cursor-position transform previously shifted
builds across chunk boundaries. Decode the blueprint positions and apply one
explicit world offset. Preflight every resulting entity center with
`can_place_entity()` and abort before placement if any position is blocked.

A settings-preserving workflow is:

1. Import the blueprint into a temporary inventory and require import status 0.
2. Build on a temporary generated surface and verify every prototype and local
   center against `get_blueprint_entities()`.
3. Use `clone_area()` with explicit rectangles to copy only entities onto the
   already-preflighted live area.
4. In the same command, verify destination prototypes, exact centers, direction,
   mirroring, recipes and qualities, and construction registration.
5. On failure, remove only matching destination ghosts. Delete temporary
   surfaces and inventories after either successful validation or rollback.

The staging workflow preserves recipes, module insert plans, and circuit and
copper wiring. Still verify the finished electric networks and bridge an internal
pole to a reachable live pole when necessary. Module requests appear as
`item-request-proxy` entities; substitutions must preserve each proxy's inventory
destinations, replace only item and quality, assign the complete plan back, and
validate `item_requests`. Inventory qualities from
`LuaLogisticNetwork.get_contents()` are strings. Inspect every connected
logistic network before selecting stock.

### Entity Ghost Inspection And Cloning

For a GPS-directed inspection, resolve the supplied surface or use the requesting
player's current surface. Search nearby `entity-ghost` entities and report
`ghost_name`, `ghost_type`, position, force, quality, unit number, and
`is_registered_for_construction()`.

Equipment and inventory requests on a vehicle ghost are not represented by its
runtime `grid`, which can be empty. Read both of these properties instead:

- `item_requests` is the read-only item/count summary.
- `insert_plan` is the exact writable blueprint plan, including inventory slot
  destinations and equipment-grid counts.

`LuaEntity.clone{position=..., surface=..., force=...}` preserves the ghost
prototype, direction, quality, `item_requests`, and complete `insert_plan`. Use
this sequence:

1. Require a current explicit request and locate the source ghost read-only.
2. Verify the requesting player is online and resolve their live surface and
   position.
3. Constrain `find_non_colliding_position_in_box()` to the requested destination.
4. Snapshot requests and the insert plan, then clone once. Treat cloning as
   unsafe to replay automatically after an RCON disconnect.
5. Compare the clone's prototype, direction, quality, requests, and insert plan
   to the source. Destroy only the new clone if validation fails.
6. Print the actual result through RCON and send the verified clone position as
   a clickable GPS link.

Construction robots may fulfill the new ghost immediately if the network has
the requested items, so verification should happen in the same Lua command as
the clone. Never destroy or alter the source ghost.

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

### Logistic Group Mutation

Named groups belong to a force. Use `LuaForce.create_logistic_group()`,
`get_logistic_group()`, and `delete_logistic_group()` with the intended
`defines.logistic_group_type`; the default `with_trash` type supports request and
auto-trash limits. `get_logistic_group()` returns group information, not a
directly writable group object. Write filters through a manual member
`LuaLogisticSection.filters` or `set_slot()`.

To create a populated but unattached group safely:

1. Abort if the exact group name already exists.
2. Create a disposable entity and manual section without raising build events.
3. Set and validate the manual filters, create the force group, then assign the
   section's `group` name.
4. Verify the shared group's complete filter set before detaching the section.
5. Clear the section's group, remove it, destroy the disposable entity, and
   verify that the populated group persists with zero members.
6. Wrap the operation in `pcall`; on failure destroy only temporary state and
   delete only the newly created group.

Existing populated groups can be edited through any valid manual member section.
Snapshot the old filters, assign the complete replacement array once, verify the
shared group and all requested limits, and restore the snapshot on failure. Never
replay a mutation automatically after an uncertain RCON disconnect.

`LogisticFilter.min=0,max=0` requests nothing and retains nothing. A nonzero
minimum requires an exact quality and `=` comparator; it cannot use an any-quality
range. To request one quality while preserving zero limits for the others, split
the item into one filter per quality. In the current unmodded quality set these
are normal, uncommon, rare, epic, and legendary.

Derive GUI-tab membership from prototypes instead of a hand-maintained list. For
example, the current `intermediate-products` item group contains 85 item
prototypes and no fluid prototypes. Verify the live count before mutation because
mods or game updates can change it.

A bare `/silent-command` executes no mutation and normally returns empty. Empty
RCON output is never proof of success. Every mutating command must print its
verified result, and important changes should receive an independent read-only
verification before a success message is sent.

### Logistic Production Cells

A reusable production cell consists of a crafting machine, a requester chest and
input inserter, and an output inserter and passive provider chest. Prefer cloning
a working cell so inserter choices, directions, and chest limits are preserved.
Validate each exact planned position with `can_place_entity()` and inspect the
complete new footprint rather than relying on an expanded search that may include
valid neighboring machines.

Do not rely on `can_place_entity(..., build_check_type=script_ghost)` alone to
protect existing infrastructure: live testing showed that it can accept a ghost
plan overlapping belts. Before creating anything, scan the complete destination
bounding box for existing entities and ghosts, especially belts, underground
belts, splitters, pipes, and wiring components. Treat any unplanned occupancy as
blocked and choose another location.

After setting the machine ghost's recipe, reproduce the player's recipe paste
onto the requester ghost with:

```text
requester_ghost.copy_settings(assembler_ghost, player)
```

This lets Factorio calculate request buffers. Validate through
`requester_ghost.get_logistic_sections().sections` that every recipe ingredient
appears as `filter.value.name` with a positive `filter.min`; do not estimate
quantities from chest contents. Locate source entities by name and position and
confirm their unit numbers because players may rebuild them.

Preserve a player-preplaced assembler: verify its state, set only the requested
recipe, and create only peripheral ghosts. Wrap multi-cell work in one `pcall`,
preflight every cell before the first change, and retain changed entities and new
ghosts for precise rollback. Verify settings and construction registration in
the same command because robots may fulfill ghosts before the next RCON query.

Power must be validated separately from placement and logistic coverage. Before
creating a cell, locate a real electric pole, verify `pole.electric_network` is
not `nil`, read its quality-aware supply radius with
`pole.prototype.get_supply_area_distance(pole.quality)`, and place the assembler
inside that area. Also verify the requester with
`surface.find_logistic_network_by_position()`.

If the destination lacks coverage, treat a power extension as a separately
validated subplan in the same `pcall`. Choose a collision-free pole in
construction coverage, verify its quality-aware supply area, require copper-wire
reach to a live network, and include its ghost in rollback. Once built,
`assembler.is_connected_to_electric_network()` is the definitive power check.

### Automatic Research Control

The current save's circuit-driven research is controlled by the `set_research`
option on one lab. Discover the active control lab before changing anything:

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

The current profile is `openai`. It uses OpenCode's configured `openai` auth from
`~/.local/share/opencode/auth.json`; never read or print the token. `ask_ai()`
runs an isolated, tool-denied `opencode run --pure --agent jimbo --format json`
from `/tmp/opencode`, with project configuration and external skills disabled.
The built-in OpenAI auth plugin must remain enabled, so do not set
`OPENCODE_DISABLE_DEFAULT_PLUGINS=1`. Transient timeouts, rate limits, and common
HTTP 5xx failures get three total attempts; permanent failures fail immediately.
Model identity is derived from the selected profile.

### Provider History

Jimbo began on local Ollama, moved to hosted DeepSeek because the local model
competed with the Factorio client for GPU memory, and moved to OpenAI after the
free DeepSeek quota was exhausted. The predefined profiles retain these working
paths for manual selection; there is no automatic fallback.

### Groq

The optional `groq` profile uses `openai/gpt-oss-120b` through the
OpenAI-compatible adapter and gitignored `groq-api-key.txt`. It limits replies to
256 tokens, requests low reasoning effort, and excludes reasoning from the
response. Rate and account quotas are its main operational risk because Jimbo
normally makes two model calls per handled request.

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

## Runtime Pitfalls

### Cross-filesystem Handle Invalidation

Windows writes to the server log can invalidate WSL's open file descriptor.
Operations such as `f.tell()` may raise `ValueError: I/O operation on closed
file`. Jimbo catches both `OSError` and `ValueError` and reopens the file.

### RCON Multi-line Messages

RCON only delivers the first line of a multi-line command. Jimbo must continue
sending filtered reply lines separately through `send_jimbo_lines()`.

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
