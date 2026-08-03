# RCON & Lua Notes

Operational quirks learned from direct RCON/Lua work against the live server
(Factorio 2.1.12). Context is precious: these cost real time to rediscover.
Consult this file before composing new RCON or Lua queries, and add new
learnings here as briefly as possible.

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

## Map Pings

- Factorio chat recognizes `[gps=x,y,surface]` as a clickable map location; send
  it as raw RCON chat including Jimbo's normal prefix.
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
- Production cells: `place_production_cell` runs a read-only Phase 1 bounded
  search, then a Phase 2 preflight+mutation+verify command; the mutation uses
  `retry=False` and is never replayed after an RCON disconnect.
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
- Identify platforms in a given orbit:
  `for _,s in pairs(game.surfaces) do if s.platform and s.platform.space_location and s.platform.space_location.name == "nauvis" then ... end end`

## Ammo Item Names (2.1.12)

- The railgun projectile is `railgun-ammo` (not `railgun-dart`).
- Magazines: `firearm-magazine`, `piercing-rounds-magazine`,
  `uranium-rounds-magazine`, `shotgun-shell`, `piercing-shotgun-shell`.
- Rockets: `rocket`, `explosive-rocket`, `atomic-bomb`.
- Always enumerate `prototypes.item` for a complete list rather than trusting
  this list.
