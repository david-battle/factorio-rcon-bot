# Repository Archive

Historical and shipped content removed from the live documentation so it no
longer occupies a working context. This file is intentionally NOT linked from
any live `.md` file. Open it only when you need background on a past feature,
a removed implementation narrative, or an archived experiment write-up.

## FIX_PLAN — Shipped Item Narrative

Removed from `FIX_PLAN.md` 2026-08-25 per that file's "delete an item's section
once merged" rule. Only the shipped retrospectives moved here; active items
remain live.

### Item 3 Step 1 — Parameterized layouts (SHIPPED 2026-08-23)

Cell shapes now live as Python entity-offset tables (`standard`,
`aquilo-compact`, `belt-fed`) instantiated per live machine footprint and
serialized into both phases; the classifier picks enumerated knobs
(`layout`/`rotation`/`lanes`/`tier`) validated in Python. The belt-fed cell
(machine between two east-flowing lanes, long-handed input tap, regular output
drop, no chests, walkway power pole) shipped together with the reply-prompt
honesty rule and live placement verification. Furnace ghosts cannot carry
preset recipes, so furnace cells place with an inherent "set recipe by hand"
warning.

### Item 3 Step 2 — Worker subprocess for open-ended requests (SHIPPED AND
LIVE-VALIDATED 2026-08-24; 205 tests pass; Jimbo restarted with it)

Live: a `layout=custom` copper-cable request spawned a detached worker (PID
tracked, no RCON), a concurrent free-form belt-fed placement ran independently
without deduping against it, `JOBSTATUS` answered from stored state across
three checks, and the worker's accepted 2-iteration design was re-validated,
normalized, stamped via Phase 2, and reported truthfully (status `done_placed`,
`reported=true`, worker exited cleanly). The produced design was functional but
basic (assembling-machine-1, a 2-belt tail) — a quality/optimization concern,
not a scaffolding defect; see `FUTURE_DIRECTIONS` direction 14.

Trigger (both paths, owner decision 2026-08-24):

- Classifier: `layout=custom` joins the documented knob range. The model picks
  it when the player asks for a shape no pre-planned variant covers; Python
  validates it like any other knob value.
- Python fallback: the requested pre-planned variant exhausts every bounded
  anchor with no structurally placeable candidate (Phase 1 structural failure —
  not a support fallback, which already succeeds on its own).

Duplicate suppression: while a job for the same surface + item + rounded origin
is pending or running, new triggers reply with job status instead of spawning
another worker.

Architecture:

- The parent gathers all server facts read-only before forking: the existing
  candidate probe (compatible machines and tile dimensions), an
  occupancy/entity survey over the bounded search region (entities by name,
  position, dimensions; water and cliff coverage), live pole supply/wire
  distances, and recipe ingredients/products. The worker itself has no RCON
  connection.
- Parent forks one short-lived worker: `python jimbo.py --produce-worker
  <job.json>`. The job file carries the player's ask, dialogue context excerpt,
  survey facts, prototype facts, validator constants, and budgets.
- Loop: the model returns one complete entity-offset table per iteration in the
  exact schema Step 1 already stamps (`n/x/y/d/r` entries plus area). Python
  validates deterministically before accepting anything: schema and prototype
  existence against surveyed facts; pairwise footprint overlap from live
  dimensions; each inserter's pickup/drop target tiles exist at measured reach
  distances (regular 1.00/1.20, long-handed 2.00/2.20); belt lanes connect end
  to end and reach their inserter targets; a pole's supply distance covers the
  machine center; nothing exceeds the declared area. Validation failures return
  verbatim to the model as the next iteration's input. First valid table wins.
- Budgets (owner decision 2026-08-24): hard stop at one hour wall clock, plus a
  15-iteration runaway cap. On exhaustion the worker writes a grounded failure
  result and exits nonzero.
- One worker at a time. Jobs live under gitignored `produce_jobs/<id>/` (input
  json, log tail, result json) so a Jimbo restart can report finished results
  and reap stale jobs.

Stamping and chat flow (shape approved by owner 2026-08-24):

- The parent independently re-validates the winning table (defense in depth),
  runs a custom-plan Phase 1 ring search for a free anchor, then stamps through
  the EXISTING Phase 2 mutation path with the table embedded. The chat model
  still never places geometry directly, and the mutation stays all-or-nothing
  with full rollback.
- Chat gets one immediate acknowledgment line, then exactly one completion
  message applying today's verified-success/failure honesty rules. Follow-ups
  such as "how's it going" read pending-job status instead of triggering
  anything.

## FUTURE_DIRECTIONS — Archived Design And Experiment Write-ups

Removed from `docs/FUTURE_DIRECTIONS.md` 2026-08-25. The features these
describe are implemented and documented authoritatively in `docs/BOT_CONTRACTS.md`.

### Alert Awareness Design

Give Jimbo awareness of active game alerts (entity damage, destroyed buildings,
logistic shortages, and similar conditions) so spontaneous comments and direct
replies are grounded in what is actually happening on each surface.

The spontaneous-comment portion is implemented: `get_alerts_snapshot(client)`
mirrors `get_research_snapshot()` and returns a compact summary grouped by
surface and type, `prepare_alerts_for_prompt` debounces `no_platform_storage`
until it persists across two snapshots, and the snapshot is included in the
spontaneous prompt (active alerts can also break the already-announced
research-stall silence). Still unimplemented: `ALERTS|surface` classifier
parsing and dispatch, and including the snapshot in alert-related direct
replies.

`game.forces.player.alerts` is a table of `LuaAlert` objects. Useful fields are
the alert `type`, `target`, `surface`, `icon`, `ticks_to_live`, custom `message`,
and `show_on_map`.

The read-only query can group alerts as follows:

```text
/silent-command local f=game.forces.player;local out={};local groups={};
for _,a in ipairs(f.alerts) do
  local key=a.surface.name.."|"..a.type;
  if not groups[key] then groups[key]=0 end;
  groups[key]=groups[key]+1;
end;
for k,c in pairs(groups) do out[#out+1]=k..":"..c end;
rcon.print(table.concat(out,"\\n"))
```

Potential output is `nauvis|turret_enemy:1` or
`fulgora|not_enough_construction_robots:2`. A player-directed query could use
`ALERTS|surface`, where `all` requests every surface. Include the snapshot in
spontaneous commentary and, when a `NONE` reply concerns attacks, damage,
warnings, or a problem, in the reply prompt. An empty snapshot should explicitly
say that there are no active alerts.

### Tested Implementation Findings

These findings came from successful live experiments. They constrain future
features but do not mean Jimbo currently exposes the actions automatically.

#### Chat-Linked Blueprint Inspection

The server log represented each player-linked blueprint only as an opaque token
such as `[special-item=internal_12]`; it did not contain the blueprint exchange
string, tiles, or snapping data. The numeric suffix did not match
`LuaItemCommon.item_number`: the player's reference appeared as `internal_12`
while the inspected item number was `23984495`, and the newly delivered item
number `25063642` was linked back as `internal_13`.

Read-only inspection found the first example because it was the player's only
inventory blueprint. Do not assume that association when multiple candidates
exist, and do not treat the token suffix as an API identifier.

#### Player Blueprint Inventory Delivery

On Factorio 2.1.12, an online player in remote view (observed controller type 7)
had a valid physical character and character inventory while
`LuaPlayer.get_main_inventory()` returned `nil`. For physical item delivery,
validate `LuaPlayer.character` and use the character's main inventory; still
fail safely when no physical character or inventory exists. Do not report a
player as offline merely because the current controller exposes no main
inventory.

The successful dotboard experiment selected a known empty character-inventory
slot, created the blueprint there, set its tiles and snapping metadata, then
read everything back. Verification required a nonempty blueprint, the exact 16
unique landfill tile positions, no entities, and the intended 20 x 20 relative
snap. On any setup or verification failure, clear only the newly allocated
stack. Do not insert first and then use `find_item_stack("blueprint")`, which can
select and overwrite an older blueprint.

#### Exact Blueprint Deployment

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

#### Entity Ghost Inspection And Cloning

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

#### Logistic Network Machine Conditions

Crafting machines can use the logistic network as an enable condition without a
circuit wire. Preflight every target before creating a control behavior, then set:

```text
local cb = entity.get_or_create_control_behavior()
cb.connect_to_logistic_network = true
cb.logistic_condition = {
  first_signal = {type="item", name="holmium-plate", quality="normal"},
  comparator = ">",
  constant = 1200
}
```

`get_control_behavior()` can be `nil` on an uncontrolled machine; use
`get_or_create_control_behavior()` only during the authorized mutation. Snapshot
existing connection and condition values for rollback. Factorio normalizes a
normal-quality signal by omitting `type` and `quality` when it is read back, so
verify a missing quality as normal rather than rejecting it. Control status may
not update until a later tick; perform an independent read-only query and require
both the saved condition and `disabled_by_control_behavior` to match live stock.

Size a reserve threshold from available logistic stock, not total items hidden in
machines or requester chests. A requester remains active when its consumer is
disabled and in-flight robots can finish deliveries. Include the protected cargo,
the largest immediate recipe draw, requester buffers, and a margin before enabling
all consumers at once. The verified Fulgora setup uses normal holmium plate
`> 1200`: a rocket carries 1,000 plates (`default_rocket_lift_weight=1000000`,
plate weight `1000`), while the largest consumer takes 150 and its requester asks
for 100.

Rediscover machines before each mutation. On the server version used for this
earlier live test, direct unit-number lookup did not resolve these entities and
`find_entity()` did not resolve a known uncommon-quality machine at its exact
position. A surface `find_entities_filtered()` scan followed by checks of
`unit_number`, recipe, position, and quality was reliable. Unit numbers are
evidence for the current entity only and become stale after rebuilding.

#### Production Shortage Diagnosis

Trace a stalled product backward one ingredient at a time. Start with logistic
availability, but do not present `LuaLogisticNetwork.get_contents()` as total
ownership: requester chests and crafting-machine input buffers can hold large
quantities while available stock is zero. Enumerate positive requester filters,
their current contents, consuming recipes, and complete machine input inventories.
Idle one-off mall recipes can sequester hundreds of expensive intermediates.

Interpret `LuaEntity.status` before assigning a cause. `full_output` means that
machine is not currently consuming ingredients; `item_ingredient_shortage` does
not identify which item is absent; and `fluid_ingredient_shortage` should be
confirmed from `get_fluid_contents()`. Check every required ingredient and the
downstream output path. In the verified Nauvis case, utility science had ample
frames and low-density structures but no available processing units; most
processing-unit machines were then found starved of advanced circuits.

Keep fluid locations separate. A surface-wide fluid total can combine unrelated
pipe systems: Nauvis simultaneously had an almost empty main petroleum tank and a
full remote tank. Report tank positions and inspect connectivity before claiming
that stored fluid can reach a consumer. Likewise, a bidirectional pump only moves
existing fluid; it cannot solve missing production on the far side.

All pumpjacks reporting `working` proves operation, not adequate throughput. If
crude storage remains nearly empty while refineries and consumers are starved,
extraction is below demand; speed modules or additional wells address sustained
throughput more directly than changing pump direction. Inspect pumpjacks through
their status and `mining_target`; crafting-machine-only properties raise errors on
mining drills.

Large per-entity RCON reports can time out. Aggregate counts, status groups,
buffers, and a few sample positions in Lua, or filter directly by prototype name,
then run focused follow-up queries on the identified area.

#### Quantitative Recipe And Rocket Calculations

Live Factorio 2.1.12 inspection established several useful calculation inputs.
`electromagnetic-science-pack` requires `magnetic-field` exactly 99; the live
properties were 99 on Fulgora, 90 on Nauvis, 25 on Gleba and Vulcanus, and 10 on
Aquilo. Its final recipe is therefore Fulgora-only even though several
intermediate recipes have no surface condition.

Scrap recycling uses one shared random interval: holmium ore occupies 0.59–0.60,
so its base expected yield is 1%. The live player force had
`scrap-recycling.productivity_bonus=0.4`, and electromagnetic plants have 50%
base productivity. Chaining the live science, supercapacitor, superconductor,
electrolyte, holmium-plate, and holmium-solution recipes gives roughly 78,000
scrap/min for 1,000 science/min before productivity modules. This is an
assumption-specific calculation, not a permanent constant; recalculate from live
bonuses and installed modules.

The live rocket silo had lift weight 1,000,000 and scrap weight 2,000, so one
rocket carries 500 scrap. Exporting 3,000 scrap/min requires six launches/min.
Normal-quality Space Age silos have an animation-bound quick-launch interval of
about 1,614 ticks (26.9 seconds), or about 2.23 launches/min, so the ideal lower
bound is three fully supplied normal silos. Module speed cannot shorten the
animation phases; silo quality can. Inspect actual silo qualities and ensure
rocket-part production and loading sustain the bound before calling it a
practical capacity.

#### Logistic Group Mutation

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

#### Logistic Production Cells

A reusable production cell consists of a crafting machine, a requester chest and
input inserter, and an output inserter and passive provider chest. Prefer cloning
a working cell so inserter choices, directions, and chest limits are preserved.
Validate each exact planned position with `can_place_entity()` and inspect the
complete new footprint rather than relying on an expanded search that may include
valid neighboring machines.

The first explicit-location implementation deliberately supports item-only
recipes. Live prototype inspection showed that processing units, holmium plates,
and superconductors all require fluid inputs, so a chest-and-inserter-only cell
must reject them until it has a pipe-aware layout. On Aquilo, prefer every
planned prototype with nonzero `heating_energy` to have part of its collision box
within a ≥30°C source's live `heating_radius`, and recheck this immediately
before mutation. If the bounded search finds no fully heated site, a structurally
placeable fallback may be ghosted with exact heat warnings. Existing heat sources
may occupy unused space inside the outer cell rectangle, but must not overlap an
exact planned component. For compact heated rings, put the machine on the north
side, the requester and provider chests on the southwest and south-center tiles,
and their inserters directly between the chests and machine. Prefer existing
electric supply instead of adding a cell pole, and report when the machine or
inserters lack live quality-aware supply coverage.

In Factorio 2.1, use every entry in `LuaRecipePrototype.categories` and the
`crafting-category` entity-prototype filter to discover compatible crafting
machines. Do not use the nonexistent singular `category`, and do not infer a
crafting machine from the recipe's product entity. Entity centers depend on
footprint parity: when `(x, y)` is the integer bottom-left tile anchor, a `w×h`
building is centered at `(x+w/2, y+h/2)`.

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

Power must be validated separately from placement and logistic coverage. Prefer
a real electric pole whose `electric_network` is not `nil`, read its
quality-aware supply radius with
`pole.prototype.get_supply_area_distance(pole.quality)`, and prefer an assembler
inside that area. Also inspect the requester with
`surface.find_logistic_network_by_position()`. If the bounded search finds no
fully supported candidate, a structurally safe fallback may still be ghosted,
but its exact missing power, logistics, heat, and construction support must be
reported.

If the destination lacks coverage, treat a power extension as a separately
validated subplan in the same `pcall`. Choose a collision-free pole in
construction coverage, verify its quality-aware supply area, require copper-wire
reach to a live network, and include its ghost in rollback. Once built,
`assembler.is_connected_to_electric_network()` is the definitive power check.

Named production-cell directions originally used only the player's current view
as their origin. This caused a live Aquilo request for "north of my current
location" to exclude a valid heated nook that was north of the physical
character but west of the remote view; leaving map view made the same request
succeed. The structured location now preserves both origin and direction with
`standing:north` and `view:north`. Existing explicit `view`, `standing`, bare
direction, and GPS forms remain compatible; a bare direction remains relative
to the current view.

#### Electric Network And Aquilo Power Diagnosis

Factorio 2.1 entities can be covered by more than one separate electric network.
`LuaEntity.electric_network` exposes only the primary network; inspect every
entry in `LuaEntity.electric_networks` for generators and consumers when
diagnosing an apparent cross-connection. Electric poles themselves belong to
only one network and continue to use `electric_network`.

To verify a power-switch boundary, keep the switch in its observed state, group
the relevant entities by every live network ID, and inspect the switch's
connectors with `get_wire_connectors(false)`. The
`power_switch_left_copper` and `power_switch_right_copper` connectors expose
their separate electric networks and `real_connections`; this distinguishes
actual copper wiring from an entity whose footprint merely overlaps two pole
supply areas. Use `pole.prototype.get_supply_area_distance(pole.quality)` for
the coverage check.

Do not infer current topology from the electric-network statistics GUI or from
the presence of a name in `current_output_quality_samples`. After a connected
network is split, each side can retain zero-valued historical producer
categories such as `solar-panel` or `steam-turbine`. A live Aquilo check showed
these phantom categories on both sides while all 338 panels belonged only to one
network and both turbines belonged only to the other. Require current
`electric_networks` membership and, when useful, nonzero `flow_last_tick`
production before reporting a live connection.

Live Aquilo power tests also established several useful diagnostic facts. Its
`solar-power` surface property is 1, so a normal panel produces 600 W at full
daylight and 420 W averaged across the day/night cycle. Runtime energy and flow
values used in these checks are joules per tick; multiply by 60 for watts.
Disabled machines and inserters retain their fixed electric drain, and
efficiency modules reduce active consumption but not that drain. An open power
switch removes the downstream drain from the charging network, so a
hysteresis latch is preferable to reconnecting a large load at one exact
accumulator threshold.

A normal roboport is especially important in a minimal bootstrap grid: its live
prototype has 50 kW drain, a 100 MJ internal buffer, and roughly 2.05 MW maximum
draw while filling or charging robots. Before recommending reconnection, inspect
both accumulator energy and the roboport buffer; an otherwise sustainable solar
grid can still brown out when an empty port is first attached.

#### Space Platform Requests And Asteroid Accounting

A minimal platform with a nearly full hub exposed a likely request-allocation
edge case. Electromagnetic plants and piercing ammunition were available on
Nauvis, but an orbital request remained idle after the platform arrived with a
full hub. Auto-trash asteroid requests later freed slots, the
`no_platform_storage` alert disappeared, and no delivery remained pending, yet
the ammunition request did not begin until the player deleted and recreated it.
That recreation immediately worked. The hypothesis that allocation was not
reevaluated after hub space changed is plausible but unconfirmed; report the
observed state and workaround rather than presenting that cause as fact.

A future platform-request diagnosis should inspect the platform's current
location and travel state, request source mode (`all` versus a named planet),
hub free slots and partial-stack capacity, auto-trash limits, pending deliveries,
planetary silo-connected logistic stock, rocket availability, and current cargo
pods before blaming item production. Request recreation is a player-approved
workaround, not a mutation Jimbo should perform automatically.

For tight asteroid inventory control, count every place a chunk can exist:
collector storage and held chunks, both lanes of every belt, hub inventory,
inserter hands into and out of crushers, and crusher input, output, and
in-crafting contents. Crushers can create extra asteroid chunks, and inserter
hand readers accidentally set to pulse instead of hold create accounting gaps.
Even complete hold-mode accounting can overshoot a target by one when multiple
collectors or machines act on the same positive request signal in the same
update window. Diagnose wiring and read modes first, then describe any remaining
one-item excess as a timing race rather than an invisible inventory.

#### Automatic Research Control

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

## OPERATIONS — Archived Provider History

Removed from `docs/OPERATIONS.md` 2026-08-25. The current profile table and
selection rules remain live.

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
