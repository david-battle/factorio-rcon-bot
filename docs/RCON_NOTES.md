# RCON & Lua Notes

Operational quirks learned from direct RCON/Lua work against the live server
(Factorio 2.1.12). Context is precious: these cost real time to rediscover.
Consult this file before composing new RCON or Lua queries, and add new
learnings here as briefly as possible.

> # FIRST RULE: probe any entity field with `pcall` unless you are certain it
> reads on that entity type. Factorio often **raises an error instead of
> returning nil** for an accessor on the wrong kind of entity (e.g.
> `e.ghost_name` on a non-ghost raises "Entity is not ghost", aborting the whole
> `/silent-command`). Wrap every conditional read in
> `pcall(function() return obj[key] end)` and check both return values; do not
> assume nil means "not applicable".

## Tooling

- `rcon.source.Client.run()` takes no `retry` kwarg. Jimbo's wrapper adds
  `retry=True`; direct callers must use `client.run(cmd)` only.
- Never inline Lua into a `python3 -c "..."` string: shell and Python both
  mangle quotes. Instead write the Lua to a temp file, read it in Python, and
  pass it to `/silent-command` in one call.
- `rcon.print` accepts one string. Embedded `\n` is delivered intact over RCON
  (verified live), so `rcon.print(table.concat(out,"\n"))` works for lists.
- Keep a single RCON response under ~4 KB: a ~6 KB response hung the
  `rcon.source` client, while ~4 KB returned fine. Aggregate counts in Lua and
  split large reports into several commands. Multi-line Lua commands themselves
  run fully.

## Connection

- Factorio supports concurrent RCON connections. The `Client` context manager
  authenticates automatically, but a manually managed client must call
  `client.connect(login=True)`. A bare `connect()` opens TCP without
  authenticating and commands hang until timeout.

## Command Reference

- `/players`: all players who have played this save. `/players online`:
  currently connected players.
- `/evolution`: enemy evolution factor. `/time`: elapsed server/game time, not
  wall-clock time.
- `/version`: Factorio version. Recheck it before relying on
  version-sensitive API behavior; `game.product_version` and
  `game.build_version` do not exist.
- Plain Lua often returns nothing; use `rcon.print()` inside `/silent-command`.
- Raw RCON text without a leading slash appears in chat as `<server>`.
- Online player count: `/silent-command rcon.print(#game.connected_players)`.
- The singular `game.player` is a client-only global and is `nil` over RCON
  (live 2026-08-24: a freeform ghost-wall command indexing `game.player`
  failed with "attempt to index local 'p' (a nil value)"). Resolve a player
  server-side with `game.get_player("name")` or by iterating `game.players`.

## Map Pings

- Factorio chat recognizes `[gps=x,y,surface]` as a clickable map location; send
  it as raw RCON chat including Jimbo's normal prefix.
- The game omits the surface from a linked location when it matches the
  player's current surface: a link to another planet or platform arrives as
  `[gps=x,y,fulgora]`, while a link on the current surface arrives as a bare
  `[gps=46.8,-78.6]` with no planet. Jimbo must not guess a planet for a bare
  link and must not substitute the player's current location for the embedded
  surface of a qualified one (see the prompt contracts in `jimbo.py`).
- World chunks are 32 x 32 tiles, with boundaries and corners at coordinates
  divisible by 32.

## Query Idioms

- Current recipe of a crafting machine: `entity.get_recipe()` returns the recipe
  prototype (nil when unset); `crafting_progress` is 0..1. Machines are found by
  name (e.g. `find_entities_filtered{name="cryogenic-plant"}`) — do not assume a
  shared `type`.
- To find which technology unlocks a recipe, iterate `prototypes.technology` and
  match effects with `type=="unlock-recipe"` and `recipe==name`, then read
  researched/prerequisites from `game.forces.player.technologies[tech]`.
- Machine status is numeric. `defines.entity_status` maps name->number, so the
  value `e.status` cannot be indexed back by number (`defines.entity_status[28]`
  is nil); compare against a named constant (`e.status ==
  defines.entity_status.item_ingredient_shortage`) or reverse-map with
  `for k,v in pairs(defines.entity_status) do if v==e.status then ... end end`.
  `defines.status` is nil on 2.1.12. Example observed: `28 ==
  item_ingredient_shortage` (an assembler waiting on a missing item ingredient).
- `LuaEntity` has no `fluid_boxes` key; read fluids with
  `e.get_fluid_contents()` / `get_fluid_count(name)`.
- `LuaEntityPrototype` has no `heating_area_radius` (heating tower); probe
  prototype keys with `pcall` before use.
- Embed strings in Lua with `json.dumps(...)`; never interpolate raw input.
- Use `json.dumps(value, ensure_ascii=False)` when embedding text that may
  contain non-ASCII characters (emoji, accents) into a Lua string literal.
  Python's default `ensure_ascii=True` emits `\uXXXX`, and Factorio's Lua 5.1
  has no `\u` escape, so the whole `/silent-command` fails with "invalid escape
  sequence" — and `client.run()` returns that error text instead of raising, so
  the failure is silent unless the response is checked. Raw UTF-8 bytes inside a
  Lua string literal are fine.
- Probe unknown keys with `pcall(function() return obj[key] end)`: Factorio
  raises `"...doesn't contain key X"` on unknown keys, and `pcall` cleanly
  distinguishes present-but-nil from absent.
- Equipment (armor-grid) prototypes live under `prototypes.equipment`, not
  `prototypes.entity`. The personal roboport is `personal-roboport-equipment`
  and MK2 is `personal-roboport-mk2-equipment`; both report
  `energy_source.buffer_capacity` = 35,000,000 (35 MJ). Never index a guessed
  prototype key blind: `prototypes.equipment["personal-roboport"]` returns nil
  with `attempt to index field 'personal-roboport' (a nil value)`. When the
  exact internal name is uncertain, enumerate matches in the same command with
  `pairs()` and a substring `:find()`, printing each name and the needed field.
- On 2.1.12, an equipment's energy storage is `p.energy_source.buffer_capacity`
  in joules; 0 means no internal buffer (draws directly from the armor grid).
  The exoskeleton (`exoskeleton-equipment`) reports 0. Its raw prototype
  definition lists `energy_consumption = "200kW"` and `movement_bonus = 0.3`,
  but the Lua wrappers do not expose those keys: reading `energy_consumption`,
  `movement_bonus`, `consumption`, or `input_flow_limit` on an equipment or
  electric-energy-source prototype raises `LuaEquipmentPrototype doesn't
  contain key ...`. `pairs()` also fails on these prototypes, so probe each
  field with `pcall` and report only fields that actually read.
- `rcon.print(table.concat(out,"\n"))` for lists; prefer joining on a separator
  like `##` or `;` when the line must stay intact.
- Entity lookup: `find_entities_filtered{name=et}`, falling back to
  `{type=et}`. Prefer `find_entities_filtered()` scans over direct unit-number
  lookup; unit numbers are evidence for the current entity only and go stale
  after rebuilding.
- There is **no** `LuaSurface.find_entity_at_position` (raises "LuaSurface
  doesn't contain key ..."). `find_entity(name, position)` requires a name. To
  identify what sits at a GPS map ping use
  `find_entities_filtered{position={x,y}}` (entities whose collision box
  covers that position) or add `radius=1` to catch nearby buildings; print
  each `e.name`.
- Player corpses are entity type `character-corpse` (the internal name and type
  are the same), so `find_entities_filtered{name="character-corpse"}` and
  `{type="character-corpse"}` both find them. `game.create_chart_tag` does NOT
  exist on 2.1.12; chart tags are created only through
  `game.forces.player.add_chart_tag(surface, {position=..., icon=..., text=...})`.
  Iterate every surface with `pairs(game.surfaces)` when a request says "all".
- Enumerate platforms via surfaces where `surface.platform` is set
  (`surface.platform.name`) and planets via `surface.planet.name`.

## Chat Delivery And Print Sounds

- A plain RCON message (`Jimbo says <line>`) is a real chat message from
  `<server>` and plays the standard chat ding (`console_message`, which is
  `__core__/sound/console-message.ogg`) to players — the same sound as any
  player chat.
- `LuaForce/LuaPlayer/LuaGameScript.print(message, print_settings?)` accepts
  `PrintSettings`: `sound` (`defines.print_sound`), `sound_path` (SoundPath),
  `volume_modifier` (0..1), `color`, `skip` (defaults `if_redundant`), and
  `game_state`. `sound_path` defaults to `console_message` when omitted.
- `defines.print_sound` values verified live on 2.1.12: `never=0`,
  `always=1`, `use_player_settings=2`.
- A SoundPath is `type/name`, e.g. `utility/console_message`,
  `utility/research_completed`, `ambient/<name>`, `tile-walking/<tile>`,
  `entity-build/<entity>`, `item-open/<item>`. Raw file paths like
  `__core__/sound/console-message.ogg` are not valid SoundPaths on 2.1.12
  (all returned false in a live probe). `LuaHelpers.is_valid_sound_path()`
  exists per the docs but `LuaHelpers` is nil inside `/silent-command` on
  2.1.12, so validate a chosen sound audibly once.
- Sending chat via
  `/silent-command game.forces.player.print("Jimbo says <line>", {sound=defines.print_sound.use_player_settings, sound_path="item-move/logistic-robot"})`
  prints the line and plays only the custom sound (no ding), respecting each
  player's chat-sound setting; use `sound=defines.print_sound.always` to force
  playback. `item-move/logistic-robot` (the robotic rattle when you move a stack
  of logistic robots into an inventory) is the verified chat sound Jimbo
  uses (see `jimbo_chat_sound_path` in `jimbo.py`). Per the 2.1.12 SoundPath
  docs, item sound paths map to specific prototype fields: `item-open`/`open_sound`,
  `item-close`/`close_sound`, `item-pick`/`pick_sound`, `item-drop`/`drop_sound`,
  `item-move`/`inventory_move_sound`. For logistic-robot the move and drop fields
  both point to `robotic-inventory-move.ogg`; it has no `open_sound`, so
  `item-open/logistic-robot` silently fell back to a wrong sound.
- On each fresh map session Factorio holds the first Lua console command behind
  the achievements warning ("Please repeat the command to proceed"); it is
  silently dropped. The warning appears only in `server-console.log` while the
  RCON response stays empty, so callers cannot detect it from the response.
  Resending the **identical** command text executes it. Jimbo therefore primes
  the console at startup with a doubled no-op silent-command
  (`prime_lua_console` / `lua_console_prime_command` in `jimbo.py`) before any
  real chat; without this, Jimbo's first line after every server restart was
  lost while `jimbo_says.log` still recorded it as delivered.
- `game.print`/`force.print` output is NOT written to `server-console.log`
  (verified: `/c game.print(false)` logged only the `[COMMAND]` line, not the
  output). Jimbo therefore records every delivered chat line to the gitignored
  `jimbo_says.log` in the same `[CHAT] <server>: Jimbo says ...` format, and
  `hydrate_dialogue()` merges that file's tail with the server log by
  timestamp so restart hydration still restores Jimbo's own messages.

## Factorio 2.1.12 API Facts

- `find_entities_filtered{area=...}` bounds are **exclusive**: a `w x h` box
  anchored at tile `(x,y)` is `{{x,y},{x+w,y+h}}`, and a single tile is
  `{{x,y},{x+1,y+1}}`. A zero-area `{{x,y},{x,y}}` always returns nothing.
- `LuaSurface` has **no** `orbit` key. The old `surface.orbit` assumption is
  gone.
- `LuaSpacePlatform` has **no** `location` key. The correct members are
  `space_location` (the current orbit/planet stop) and `space_connection`
  (non-nil while traveling).
- `platform.space_location.name` is the *planet* name (`nauvis`, `gleba`, ...),
  not an `-orbit` string. `space_location.planet` does not exist; the name is
  enough. A platform mid-travel has `space_location == nil`.
- `game.item_prototypes` does not exist; item prototypes live at
  `prototypes.item` (same 2.1 rename as `prototypes.recipe`). Enumerate with
  `ip.type == "ammo"` instead of hardcoding names.
- `LuaInventory.get_contents()` changed in 2.1: it returns an array of
  `ItemWithQualityCount` (each `{name=..., quality=..., count=...}`), keyed by
  slot index, NOT the 2.0 `{name=count}` dictionary. Verified on a wooden
  chest and a platform hub. Read counts with `get_item_count(name)` or the new
  `get_item_quality_counts(name)` instead. New 2.1 inventory methods:
  `transfer_from_stack(source)` and `transfer_from_inventory(source, filter?)`.
- `game.active_mods` no longer exists on 2.1.12 (raised `LuaGameScript
  doesn't contain key active_mods`); do not rely on it.
- `game.recipe_prototypes` is gone; recipes are `prototypes.recipe`. In 2.1 a
  recipe exposes plural `categories`; do not use the nonexistent
  `LuaRecipePrototype.category`. Resolve compatible crafting machines with
  `prototypes.get_entity_filtered{crafting-category=...}`; never assume the
  recipe's product entity is its machine.
- Lua has no `chr()`; use `string.char(...)`.
- On 2.1.12, reactor prototypes (`nuclear-reactor`, `fusion-reactor`) have **no**
  `energy_source` at all — that key is absent from both `LuaEntity` and
  `LuaEntityPrototype`, and `LuaEntity` has no `get_energy_source()` method.
  They expose `neighbour_bonus` (=1, i.e. +100% per
  neighbor) and `burner_prototype` (LuaBurnerPrototype, `effectivity`=1,
  `fuel_categories`={nuclear}/{fusion}); `pairs()` on prototype userdata raises
  "bad argument to pairs", so probe keys with `pcall`. Base output is not
  readable from those keys on 2.1.12; use the known constants (nuclear-reactor
  40 MW, fusion-reactor 250 MW) and scale by `1 + neighbours*neighbour_bonus`.
- Reactor adjacency must be probed at a **±5 tile offset** (reactors are 5x5,
  edge-adjacent centers are 5 apart). `find_entity(name, pos±1)` returns the
  reactor's own bounding box and over-counts neighbors: a 61-reactor farm
  reported 244 phantom neighbors (40x5x61=12200 MW) vs the real 156
  (8680 MW). Count neighbors against the position list at ±5, not ±1.
- Concatenating right after a numeric literal is a syntax trap: `np/1e6..' MW'`
  fails with `malformed number near '1e6..'` because Lua's lexer absorbs the
  first `.` of `..` into the number. Put a space or parentheses around it:
  `.. (np/1e6) .. ' MW'`.

## Verified Runtime Facts

- On 2.1.14, `LuaEntity.order_deconstruction(force)` returns a boolean: `true`
  means the entity was newly marked for deconstruction, `false` means it was
  not (already marked or not deconstructable) — not an error string. It never
  raises on an ordinary deconstructable entity, so a pcall-wrapped call that
  returns `false` means "already handled", not failure. The signature also
  takes optional `player` and `undo_index` parameters (verified against the
  installed runtime-api.json), so attribution to the requesting player works.
- On 2.1.14, `LuaEntity.to_be_deconstructed` is a **method**:
  `e.to_be_deconstructed()`. Reading it as a property yields the function
  itself (tostring prints "function"), silently defeating boolean checks.
- `surface.find_entities_filtered{name=X}` RAISES "Unknown entity name: X"
  when X is not a real prototype instead of returning an empty table — a
  sentinel such as `"any"` must be branched off before filtering (observed
  live in the REMOVE path on 2026-08-23).
- `game.forces.player.alerts` is a table of `LuaAlert` objects. Useful fields:
  `type`, `target`, `surface`, `icon`, `ticks_to_live`, `message`,
  `show_on_map`.
- `LuaPlayer.get_main_inventory()` returns `nil` for an online player in remote
  view (controller type 7); `player.character.get_main_inventory()` still works.
  Do not treat a missing current-controller inventory as proof the player is
  offline.
- Chat-linked blueprints appear in logs as opaque `[special-item=internal_N]`;
  the numeric suffix is not `LuaItemCommon.item_number`.
- Vehicle/entity-ghost requests: `item_requests` is the read-only item/count
  summary; `insert_plan` is the exact writable plan (slot destinations and
  equipment-grid counts). The runtime `grid` can be empty.
- `LuaEntity.clone{position=..., surface=..., force=...}` preserves the ghost
  prototype, direction, quality, `item_requests`, and complete `insert_plan`.
  Treat cloning as unsafe to replay automatically after an RCON disconnect.
- For precise remote deploy, do not call `LuaItemStack.build_blueprint()`: its
  cursor-position transform previously shifted builds across chunk boundaries.
  Decode positions, apply one explicit world offset, and preflight every entity
  center with `can_place_entity()`.
- Control behavior: `get_control_behavior()` can be `nil` on an uncontrolled
  machine; use `get_or_create_control_behavior()` only during the authorized
  mutation. Set `cb.connect_to_logistic_network = true` and
  `cb.logistic_condition = {first_signal=..., comparator=..., constant=...}`.
  Factorio normalizes a normal-quality signal by omitting `type`/`quality` on
  read-back; verify a missing quality as normal.
- `LuaEntity.status`: `full_output` means not currently consuming;
  `item_ingredient_shortage` does not identify the absent item;
  `fluid_ingredient_shortage` should be confirmed from `get_fluid_contents()`.
  Mining drills raise on crafting-machine-only properties; inspect them via
  status and `mining_target`.
- Generators and consumers can belong to several networks: inspect every entry
  of `electric_networks`, not only `electric_network`. Electric poles belong to
  one network. Switch wiring: `get_wire_connectors(false)` exposes
  `power_switch_left_copper` and `power_switch_right_copper`, each with its own
  `electric_network` and `real_connections`.
- On 2.1.12 `LuaEntity.electric_network` returns a `LuaElectricSubNetwork`, not
  a `LuaElectricNetwork`. The subnetwork is nearly bare: only `.id` reads.
  `statistics`, `supply_area_statistics`, `get_entity_suppliers()`,
  `get_entity_consumers()`, `network_id`, `network`, and `wire_count` all raise
  "LuaElectricSubNetwork doesn't contain key ...". `game.electric_networks` is
  not a usable accessor for full-network statistics either.
- Use `LuaEntity.electric_networks` (plural) to test whether two subnetwork ids
  are really one merged network: an entity bridging them lists every id, e.g. a
  solar panel on a bridge row and the rocket silo both reported `{137,2898}`.
  Poles expose only the singular `electric_network`; their plural list is empty.
- A pole whose in-game electric-network GUI shows nothing is the symptom of an
  isolated subnetwork. Diagnose by reading the pole's subnetwork id, then the
  plural `electric_networks` of nearby generators/consumers; a consumer listing
  only a different id means a wiring gap (pole out of wire reach) split the
  networks.
- `find_entities_filtered{area=...}` bounding boxes are a two-element list of
  Positions: `area={{x1,y1},{x2,y2}}`. The nested `{{{x1,y1}},{{x2,y2}}}` form
  raises "real number expected got table", aborts the whole command, and spams
  the in-game console with errors.
- Empty network statistics are `nil`, not `{}`: guard with
  `for k,v in pairs(n.statistics.input_counts or {})` or the loop raises
  "bad argument #1 to 'pairs'".
- `pole.prototype.get_wire_reach_distance(pole.quality)` raises
  "LuaEntityPrototype doesn't contain key get_wire_reach_distance" on 2.1.12;
  `get_supply_area_distance(pole.quality)` works. Detect a pole gap by comparing
  subnetwork ids of neighboring poles instead of wire reach.
- Power coverage: `pole.prototype.get_supply_area_distance(pole.quality)`;
  `assembler.is_connected_to_electric_network()` is the definitive check.
- Logistic groups belong to a force: `LuaForce.create_logistic_group()`,
  `get_logistic_group()` (returns info, not a writable group), and
  `delete_logistic_group()`. Write filters through a member
  `LuaLogisticSection.filters` or `set_slot()`.
- `LogisticFilter.min=0,max=0` requests and retains nothing. A nonzero minimum
  requires an exact quality and `=` comparator; use one filter per quality.
- Logistic filter slots expose `min`/`max` (no `count` field). A filter whose
  signal is a platform/space import has `name=nil`, `value` as a table, and an
  `import_from` field; don't assume `name`/`count` always exist.
- Recipe paste onto a requester ghost: `requester_ghost.copy_settings(
  assembler_ghost, player)`; validate via
  `get_logistic_sections().sections` filters.
- `can_place_entity(..., build_check_type=script_ghost)` can accept a ghost
  plan overlapping belts; scan the full destination bounding box first.
- Entity centers: with the integer bottom-left tile anchor `(x, y)`, a `w x h`
  building is centered at `(x+w/2, y+h/2)`.
- Large per-entity RCON reports can time out; aggregate counts and status groups
  in Lua, then run focused follow-up queries.
- Automatic research is driven by a lab's `get_control_behavior().set_research`;
  discover it with `find_entities_filtered{type="lab"}` and toggle the flag.
- Windows writes to the server log can invalidate WSL's open file descriptor;
  `f.tell()` may raise `ValueError`. Reopen the file on `OSError` or
  `ValueError`.
- On 2.1.14, player personal logistics requests moved to
  `player.character.get_logistic_sections()` (returns `LuaLogisticSections`).
  `player.get_character_logistic_requests()`,
  `player.get_logistic_requests()`, and `player.logistic_requests` are all gone
  (raise "doesn't contain key"). Match item by filter `name`; `min` is the
  request threshold and `max` may be nil. Empty slots print `name=nil`.
  Use `pairs(game.players)` (includes offline players) not `game.get_player`
  (online only). The equipment's internal name is `battery-mk2-equipment`, not
  `personal-battery-mk2-equipment`.
- On 2.1.14, requester-chest filter slots store `value` as a table (with
  `import_from` and other keys), not the bare string seen on 2.1.12; probe
  `type(f.value)` before treating it as a name. Also
  `LuaInventory.get_item_count(name)` rejects the name argument on 2.1.14
  ("Expected 0 or 1 arguments but 2 were given"); sum
  `inv.get_contents()` entries (`name`/`count`) instead.
- On 2.1.14, `defines.direction` prints eight directions at even steps:
  north=0, north-east=2, east=4, south-east=6, south=8, south-west=10,
  west=12, north-west=14. Belt and inserter `direction` reads use these
  values (cardinals are multiples of 4), so never assume the documented
  0-7 encoding when comparing raw numbers.
- Inserter reach measured live on 2.1.14 via `LuaEntity.pickup_position` /
  `drop_position`: regular inserters pick up 1.00 tiles from center and drop
  at 1.20; long-handed pick up at 2.00 and drop at 2.20. `inserter_arm_length`
  is not exposed on prototypes (raises).
- Creating an `entity-ghost` of a furnace accepts a `recipe=` argument but
  silently drops it (`get_recipe()` returns nil); `set_recipe` raises
  "Entity is not assembling-machine". Furnace ghosts therefore cannot carry
  a preset recipe.
- `LuaEntity.cancel_deconstruction` returns nil, not a success flag; confirm
  cancellation by re-scanning `to_be_deconstructed()`.
- `create_entity` snaps positions that are not valid entity centers to a
  nearby valid position rather than failing: a 1x1 ghost asked for x=261
  (integer) landed at x=261.5. Give 1x1 entities half-tile centers.
- Creating an `entity-ghost` WITHOUT an explicit `force` defaults it to the
  `enemy` force (live 2026-08-24): RCON could see the ghosts but players saw
  nothing and could not build them. Always set `force=game.forces.player` on
  `create_entity` for player-visible ghosts. Do not destroy entities while
  iterating a `find_entities_filtered` result directly; the iteration and any
  count both become unreliable.

### "Who Is Requesting Item X?" — Working Recipe (2.1.14)

First-check player personal requests before scanning the map: bots snatching
freshly crafted items out of the player's inventory almost always means another
player (possibly AFK) has a personal logistics request open — requester chests
and vehicle `item_requests` come back empty. Probe a player with:

```lua
local ls = player.character.get_logistic_sections()
for _, sec in pairs(ls.sections) do
  if sec.filters then
    for _, f in pairs(sec.filters) do
      if f.name == item then
        -- match: player.character requests item, min=f.min, max=tostring(f.max)
      end
    end
  end
end
```

Do not scan every entity on a surface (`find_entities_filtered{}` then
`get_logistic_sections()`/`item_requests` on each) — that hung the live server
for over a minute. Target `type="logistic-container"`, `"car"`,
`"spider-vehicle"`, and `"entity-ghost"` individually if a map-side requester is
genuinely expected.

## Built-in Jimbo Queries

`jimbo.py` holds the executable implementations; keep them authoritative rather
than copying the Lua here.

- Chart tags: `run_tag_command` / `run_untag_command` / `run_top_damage_command`
  use `game.forces.player.add_chart_tag(s,{position=...,icon={type='entity',
  name=...},text=...})`, `find_chart_tags(s)`, and `tag.destroy()`.
- Logistics availability: `get_logistic_availability` discovers player networks
  through roboports and dedupes them by `network_id`, links silos with
  `find_logistic_network_by_position()`, and sums `max(0,count)` per item across
  `LuaLogisticNetwork.get_contents()`.
- Production cells: `place_production_cell` runs a read-only candidate probe
  (compatible machines and tile dimensions), a read-only Phase 1 bounded
  search over Python-built layout variant tables, then a Phase 2
  preflight+mutation+verify command; the mutation uses `retry=False` and is
  never replayed after an RCON disconnect.
- Research: `get_research_snapshot` reads `game.forces.player.current_research`,
  `research_progress`, and `research_queue`.
- Alerts: `get_alerts_snapshot` groups `game.forces.player.alerts` by
  `surface|type` with counts via `rcon.print`, returning `(no active alerts)`
  when empty. `prepare_alerts_for_prompt` debounces `no_platform_storage` until
  it persists across two snapshots because it can fire briefly while orbital
  requests are allocated.

## Platform Cargo

- Platform cargo lives on the `hub` entity inventories
  `defines.inventory.hub_main` (cargo) and `defines.inventory.hub_trash`.
  `space_platform_hub` is not a valid inventory index in 2.1.
- `defines.inventory` on 2.1.12 has `hub_main=1` and `hub_trash=2`, but NO
  `cargo_bay` constant: reading `defines.inventory.cargo_bay` is nil and
  `entity.get_inventory(nil)` raises `'inventory index': real number expected
  got nil`. Probe a cargo-bay entity's inventory indices with `pcall` rather
  than guessing.
- Identify platforms in a given orbit:
  `for _,s in pairs(game.surfaces) do if s.platform and s.platform.space_location and s.platform.space_location.name == "nauvis" then ... end end`

## Space Platform Requests (2.1.12)

- `LuaSpacePlatform.get_imports()` and `get_requesting()` (the 2.0 API) DO NOT
  exist on 2.1.12 — they raised `LuaSpacePlatform doesn't contain key ...`.
  Platform import/build requests now live on the hub entity's logistic
  sections: `platform.hub.get_logistic_sections().sections`.
- Each `LuaLogisticSection` has a `.filters` array. Filters are plain Lua
  tables (`pairs()` works) with NO `signal` or `name` key — item identity is
  `value` (internal item name string). Observed fields: `value` (string),
  `min`, `max` (nil when unset), `import_from` (`LuaSpaceLocationPrototype` or
  nil; `.name` is the planet name, e.g. `nauvis`; prints as
  `[LuaSpaceLocationPrototype: nauvis (planet)]`), `request_from` (string;
  observed `all` and `platforms`, absent/nil when unset). This differs from
  logistic-group filter slots (see Verified Runtime Facts), where `value` is a
  table.
- `LuaLogisticSection` has no `name` key on 2.1.12 (`sec.name` raises
  `doesn't contain key name`).
- The hub's "Provide materials to other platforms" checkbox has no read/write
  API on 2.1.12 (a `LuaEntity.provides_to_other_platforms` attribute was only
  added in a later release per the forums); trust the player's GUI state.
- Platform-to-platform providing gotcha: a platform will NOT dispatch an item
  to another platform in the same orbit while the provider itself has an
  active import request for that item — its stock is reserved for its own
  request. Diagnose by reading the provider's hub sections: any filter whose
  `value` is the item with a nonzero `min` blocks sharing, so the requester
  never shows it "on the way". The fix is removing or disabling the provider's
  own request for that item.

## Ammo Item Names (2.1.12)

- The railgun projectile is `railgun-ammo` (not `railgun-dart`).
- Magazines: `firearm-magazine`, `piercing-rounds-magazine`,
  `uranium-rounds-magazine`, `shotgun-shell`, `piercing-shotgun-shell`.
- Rockets: `rocket`, `explosive-rocket`, `atomic-bomb`.
- Always enumerate `prototypes.item` for a complete list rather than trusting
  this list.

## Custom-cell worker (Step 2) Lua learnings (2.1.14)

- Entity footprint `w x h` for offset tables comes from
  `prototypes.entity[name].tile_width` / `.tile_height`. The building's own
  offset (its center relative to the machine's top-left) is `w/2, h/2`.
- Survey commands use `find_entities_filtered{area={...}}` (area boxes are
  `{{x1,y1},{x2,y2}}`), `get_tile(x,y).name:find('water')` for water samples,
  and `find_entities_filtered{type='cliff'}` for cliffs.
- Medium pole reach reads `prototypes.entity['medium-electric-pole']
  .get_supply_area_distance('normal')` and `.get_max_wire_distance('normal')`.
- Recipe ingredients enumerate `prototypes.recipe[name].ingredients` with
  `ingredient.amount` and `ingredient.name` (same pattern as elsewhere).
- The worker subprocess itself never talks RCON; it only reads the JSON facts
  the parent gathered. All 2.1.14 prototypes are already captured via the
  parent's read-only survey commands above.
