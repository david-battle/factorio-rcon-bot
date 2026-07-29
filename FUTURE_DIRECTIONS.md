# Future Directions

Jimbo should become more aware of what is happening across the server without
turning into a noisy monitoring system or requiring players to memorize exact
commands. These are ideas to explore, not committed implementation plans. Any
work should preserve the bot's simple architecture and favor useful context,
natural interaction, and restrained behavior.

1. **Refine shared conversational context.** The first bounded server-wide
   dialogue is implemented: 12 turns, 15 minutes, about 4,000 characters, Jimbo's
   delivered replies, relevant RCON facts, and restart hydration. Future work
   should tune those limits only from observed chat and consider richer context
   only when a concrete failure remains. See `CONVERSATIONAL_CONTEXT_PLAN.md` for
   the implemented design and validation criteria.

2. **Event-aware commentary.** Parse meaningful activity into recognizable events
   instead of treating every log line as equivalent raw text. Research
   completions, deaths, launches, joins, leaves, and other milestones could give
   Jimbo better material for timely, grounded comments. Event awareness should
   improve relevance without making Jimbo react to everything.

3. **Natural situational awareness and proactive warnings.** Jimbo should be able
   to answer broad questions about how the factory is doing without requiring a
   letter-perfect command or one hard-wired status query. Existing exact phrases
   and meme commands should be reviewed for places where normalized or fuzzy
   intent matching would feel more natural. The same situational awareness could
   let Jimbo notice important conditions on Nauvis or other planets, especially a
   power network approaching failure, and warn players as a human teammate might.
   The difficult design questions are which facts matter, how often to inspect
   them, and what thresholds justify speaking up.

   One observed intent failure is that questions asking what kind of space ship to
   build are classified as requests to list existing platforms. Jimbo then treats
   platform names or their item markup as design recommendations. Future intent
   work should distinguish platform inventory questions from ship-design advice
   and avoid presenting a platform query as relevant evidence for the latter.

4. **Grounded production diagnosis and bounded controls.** Jimbo should answer
   broad questions such as "where are all the processing units going?" by tracing
   production backward through actual logistic stock, requester and machine
   buffers, recipe ingredients, entity statuses, fluid systems, and extraction
   throughput. It should identify the first verified bottleneck and relevant map
   locations rather than guessing from one empty inventory. With an explicit
   request, the same grounded model could apply reversible logistic-network enable
   conditions to reserve cargo or protect scarce ingredients. The tested findings
   below capture the important API and threshold details.

5. **Grounded GPS and construction actions.** A bare message such as
   `Jimbo [gps=362.1,-503.6]` is currently treated as conversation, so Jimbo may
   claim it is traveling there without inspecting anything. Recognize GPS-only
   engagement as an area-inspection request or ask what the player wants checked;
   never imply movement or observation without RCON evidence. Verified RCON
   techniques can inspect and clone entity ghosts with their inventory/equipment
   plans, ping exact locations, toggle circuit-controlled research, and create
   compact powered logistic production cells. Use the tested APIs and safety
   constraints below before turning any of them into Jimbo features.

6. **Formal offline scenario harness.** The project already supports manual log
   injection and mocked AI or RCON checks. Formalize that capability into a small,
   deterministic scenario harness for complete flows such as chat classification,
   follow-up replies, joins, spontaneous comments, failures, and fuzzy trigger
   matching. It should remain lightweight and should not introduce a testing or
   configuration framework larger than the bot itself.

7. **Optional provider fallback.** Jimbo's model profiles are intentionally
   self-contained so a future explicit fallback order could reuse them without
   duplicating provider configuration. If pursued, fallback should remain
   optional, preserve the normal retry behavior, report the model that actually
   answered, and avoid silently switching models for permanent configuration or
   authentication errors.

8. **Bounded one-chunk blueprint design.** The old repository contains useful
   standard-library patterns for strict blueprint encoding/decoding, exact
   doubled-coordinate geometry, nominal footprint validation, and deterministic
   encode/decode artifact tests. A future first implementation should extract
   only a small codec and 32 x 32 validator with explicit limits, exceptions,
   versioned live-verified prototype footprints, and one known test fixture. The
   model should propose bounded structured entities; local code, not the model,
   should create the opaque exchange string.

   Keep artifact generation separate from deployment. Prove the offline codec
   and validator first, then choose a reliable in-game delivery path, verify
   import through Factorio, and only later consider optional live placement using
   the preflight, staging, clone, audit, and rollback procedure below. Do not
   import the old full-bot architecture, RCON wrappers,
   complete solar/QUP generators, optimizer assumptions, or Factorio 2.1.11
   prototype tables. Those are design references, not a general current runtime
   framework.

9. **Player-delivered utility blueprints.** A concrete player request from
   2026-07-29 was for a grid-snapped "sandfill dotboard" blueprint delivered to
   the player's inventory. The example the player subsequently linked confirms
   that "sandfill" meant the vanilla landfill tile and that "dotboard" meant a
   sparse repeating board of isolated tile dots for Spidertron travel, not a
   solid landfill chunk. The linked tile-only example contains ten landfill
   tiles in a relative 20 x 20 snap cell, at `(0,0)`, `(14,2)`, `(8,4)`,
   `(2,6)`, `(16,8)`, `(10,10)`, `(4,12)`, `(18,14)`, `(12,16)`, and `(6,18)`.
   Because the player described it as "something like this," treat that geometry
   as a concrete reference pattern rather than assuming exact reproduction is
   required.

   The player expressed no preference between a 20 x 20 or 32 x 32 repeat cell
   and expected a regular rather than offset grid. Blueprint snap dimensions are
   independent of Factorio's 32 x 32 world chunks, so "snaps to grid" alone does
   not imply a chunk-sized or absolute grid. A direct live prototype used a
   20 x 20 relative snap cell with a 4 x 4 square lattice of single landfill
   tiles spaced five tiles apart. Its 16 tiles, empty entity list, label, and
   snapping metadata were verified after delivery. The player reported that it
   looked as though it would work and repeat properly. Treat this as a
   provisional useful design until an actual Spidertron traversal confirms it.

   Jimbo's first improvised command would only have inserted an empty labeled
   blueprint with snapping metadata, and both it and the first direct retry
   failed to find a player-level inventory because the player was in remote
   view. A future implementation should use bounded local pattern generation and
   the verified physical-character delivery procedure below. It does not need
   the entity-layout codec or deployment pipeline from direction 8 merely to
   create a tile-only inventory blueprint.

Context and factual knowledge are separate problems. A larger dialogue window
would not have prevented the incorrect solid-fuel energy answer, and the current
server log does not expose enough information to answer session death counts.
Prototype values, technology effects, and similar factual questions should
eventually use targeted RCON/Lua queries. Death tracking would require explicit
game instrumentation or another reliable event source rather than model memory.

Live chat on 2026-07-29 exposed the trust cost of leaving quantitative mechanics
on the `NONE` path. Jimbo confidently estimated 2,000–3,000 scrap/min for 1,000
electromagnetic science/min, two silos for 3,000 scrap/min, and a one-second silo
animation without querying or calculating. Players responded with “Do NOT trust
AI” and “this one especially.” A correction restored the immediate facts but
did not restore confidence. Quantitative questions should therefore route to a
small grounded calculation path that:

1. queries live recipe products, shared probabilities, surface conditions,
   force recipe productivity, machine base effects, item weight, rocket lift
   weight, entity quality, and timing fields as relevant;
2. states the assumptions and the few conversion factors that control the
   result;
3. separates a hard lower bound from a practical recommendation; and
4. declines when the live data cannot support the calculation.

Do not classify an export feasibility question as `PLATFORMS` merely because it
mentions interplanetary shipping; a list of platform names says nothing about
recipe feasibility or throughput. Also avoid Markdown emphasis in raw Factorio
chat because it is delivered literally rather than rendered.

The strongest product direction is a combination of event-aware context and
natural situational awareness, including grounded production diagnosis. A useful
first exploration would identify the small set of server conditions Jimbo should
understand continuously, beginning with per-surface power health, then decide how
players can ask about those conditions conversationally and when Jimbo should
mention them unprompted.

## Tested Implementation Findings

These findings came from successful live experiments. They constrain future
features but do not mean Jimbo currently exposes the actions automatically.

### Chat-Linked Blueprint Inspection

The server log represented each player-linked blueprint only as an opaque token
such as `[special-item=internal_12]`; it did not contain the blueprint exchange
string, tiles, or snapping data. The numeric suffix did not match
`LuaItemCommon.item_number`: the player's reference appeared as `internal_12`
while the inspected item number was `23984495`, and the newly delivered item
number `25063642` was linked back as `internal_13`.

Read-only inspection found the first example because it was the player's only
inventory blueprint. Do not assume that association when multiple candidates
exist, and do not treat the token suffix as an API identifier. A future
linked-blueprint workflow needs an unambiguous supported reference, or should
ask the player to hold, isolate, or export the intended blueprint.

### Player Blueprint Inventory Delivery

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

### Logistic Network Machine Conditions

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
earlier live test,
direct unit-number lookup did not resolve these entities and `find_entity()` did
not resolve a known uncommon-quality machine at its exact position. A surface
`find_entities_filtered()` scan followed by checks of `unit_number`, recipe,
position, and quality was reliable. Unit numbers are evidence for the current
entity only and become stale after rebuilding.

### Production Shortage Diagnosis

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

### Quantitative Recipe And Rocket Calculations

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

The first explicit-location implementation deliberately supports item-only
recipes. Live prototype inspection showed that processing units, holmium plates,
and superconductors all require fluid inputs, so a chest-and-inserter-only cell
must reject them until it has a pipe-aware layout. Aquilo placement is supported
only beside existing live heat infrastructure: every planned prototype with
nonzero `heating_energy` must have any part of its collision box within the
source's live `heating_radius`, and the source must be at least 30°C. Recheck
this immediately before mutation. Existing heat sources may occupy unused space
inside the outer cell rectangle, but must not overlap an exact planned component.
For compact heated rings, put the machine on the north side, the requester and
provider chests on the southwest and south-center tiles, and their inserters
directly between the chests and machine. Reuse existing electric supply instead
of adding a cell pole, and verify the machine and both inserters are inside a
live pole's quality-aware supply area.

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

Named production-cell directions currently use the player's current view as
their origin. The structured location field can express `standing` or `north`,
but not both. This caused a live Aquilo request for “north of my current
location” to exclude a valid heated nook that was north of the physical
character but west of the remote view; leaving map view made the same request
succeed. A future refinement should preserve both origin and direction, such as
`standing:north` versus `view:north`, while retaining the existing explicit
`view`, `standing`, direction, and GPS forms for compatibility.

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
