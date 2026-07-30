# Production Cell Placement

Place a compact crafting cell (building, requester chest, provider chest, two
inserters, and either a new or existing power supply) at a verified location so
construction bots can build it. The model specifies what to make; local code
handles geometry, preflight, placement, and verification. Compatible crafting
machines and their dimensions are resolved from live Factorio 2.1 prototypes
rather than a hardcoded recipe-category table.

## Architecture

The model does not choose coordinates for a relative placement. It returns only
the structured `PRODUCE|surface|item|location` decision. Python validates those
fields. Read-only Phase 1 Lua then resolves the actual current view or physical
position from the server, derives the bottom-left starting anchor for each live
compatible machine footprint, and searches deterministic expanding rings in the
requested directional sector. An explicit GPS remains the one exact anchor.

Phase 1 prefers a fully supported site and remembers the first structurally
placeable fallback. Only after it returns a validated anchor does Python build
the separate Phase 2 mutation command. Phase 2 revalidates the chosen plan,
creates and verifies the ghosts once with retry disabled, and either prints the
verified result or performs complete rollback.

Every completed Phase 1 search appends a machine-readable trace to its private
RCON response. Python removes it before reply composition and writes a compact
`PRODUCE search trace` line to `jimbo.log`. It records:

- resolved surface, exact origin, and directional sector;
- compatible-machine and anchor counts;
- structurally valid plan count;
- occupied and exactly unplaceable plan counts;
- structural plans missing heat, logistics, construction, or power support; and
- the selected strict/fallback anchor and layout, or `none`.

Compact and standard layouts may both be evaluated at one anchor, so the plan
outcome counters can sum to more than the anchor count. The trace is diagnostic
only and never relaxes mutation verification or appears in player chat.

## Current Implementation Status

Steps 1 through 5 are implemented for an item-only recipe. The current code:

- classifies requests into `PRODUCE|surface|item|location`, distinguishing an
  explicit GPS ping, current remote view, physical character position,
  normalized direction with an optional explicit view or standing origin, and
  an omitted location;
- resolves `current` to the connected player's viewed or physical surface,
  searches from the requested origin, and falls back to the requested surface's
  actual force spawn when an omitted location has no matching online view;
- strictly validates the GPS coordinates, requires its surface when present to
  match the requested surface, and floors the coordinates to a bottom-left tile;
- rejects locked recipes, fluid ingredients or products, and recipe/surface
  mismatches before mutation;
- resolves compatible placeable crafting machines through
  `r.categories` and `prototypes.get_entity_filtered()` and prefers faster,
  smaller candidates;
- reads live dimensions, scans the complete footprint for occupancy, checks
  logistic and construction coverage, verifies that the planned pole can power
  the building, and searches up to two fully preflighted extension poles when
  the cell pole cannot reach live power directly;
- searches deterministic expanding rings, using footprint-sized steps normally
  and tile-sized steps on Aquilo, bounded to 128 tiles and 256 anchors per
  compatible machine, and applies the requested directional sector before
  running the same placement checks;
- on Aquilo, checks whether each freezable planned component touches an existing
  heat pipe, reactor, or heat interface at 30°C or warmer, while allowing
  non-overlapping heat infrastructure to remain inside the outer cell rectangle,
  and first tries a five-entity heated-ring layout powered by existing poles;
- prefers a candidate with heat, live power, logistics, and construction
  coverage, but remembers the first structurally placeable fallback and uses it
  with explicit support warnings if the bounded search finds no fully supported
  candidate;
- repeats every structural and support preflight immediately before mutation;
- creates the selected five- or six-ghost layout plus any extension poles
  without mutation retry,
  copies the machine recipe settings to the requester chest through the
  requesting player, verifies every ingredient request, the assigned recipe,
  and construction registration, and destroys and checks all newly created
  ghosts if the mutation fails.

The following details are deliberately not implemented yet:

- shifting the fixed cell or pole layout when the bounded extension search is
  blocked;
- caching live prototype dimensions across requests (Step 6);
- fluid-capable cells with pipe or barrel handling;
- independent read-only post-mutation verification.

## Cell Layout

The building's bottom-left tile is the anchor `(x, y)`. All other positions
are relative to the building's dimensions `(w, h)` queried at runtime from
the compatible crafting-machine prototypes selected from every category in
`prototypes.recipe[item-name].categories`.

```
[Req] [In] [Building w×h] [Out] [Prov]
                    Power pole below the building center
```

| Component | Position | Notes |
|---|---|---|
| Building | entity center `(x+w/2, y+h/2)` | Occupies tiles from the bottom-left anchor across `w×h` |
| Input inserter | `(x-0.5, y + floor(h/2) + 0.5)` | Picks up on its west side and drops into the building |
| Requester chest | `(x-1.5, y + floor(h/2) + 0.5)` | One tile west of the input inserter |
| Output inserter | `(x+w+0.5, y + floor(h/2) + 0.5)` | Picks up from the building and drops east |
| Provider chest | `(x+w+1.5, y + floor(h/2) + 0.5)` | One tile east of the output inserter |
| Power pole | `(x + floor(w/2) + 0.5, y-0.5)` | One tile row below the building |

Both inserters use `defines.direction.west`: Factorio inserters pick up behind
and drop in front, so this moves material west-to-east through the cell.
Half-tile coordinates keep odd-width entities centered on tiles and even-width
entities centered on tile borders.

On Aquilo, Jimbo first tries this heated-ring layout with no new pole:

```
[ Building w×h at the north/top ]
[ In] [Out]  between chests and building
[Req] [Prov] at the south/bottom
```

The requester and provider are at `(x+0.5, y+h+1.5)` and
`(x+1.5, y+h+1.5)`. Their inserters are immediately north at
`(x+0.5, y+h+0.5)` facing south and `(x+1.5, y+h+0.5)` facing north.
The fully supported compact candidate has the machine and both inserters covered
by a powered electric pole. A structural fallback may lack that coverage and
reports it explicitly. If the compact plan does not fit, the standard layout is
still checked.

Every position is preflighted with `can_place_entity()` before any ghost is
created. The full bounding box is a union of all component rectangles.

## Classifier Integration

The model returns a new structured line during classification:

```
PRODUCE|surface|item-name|optional-position-hint
```

- `surface` — lowercase internal surface name such as `nauvis` or `fulgora`.
- `item-name` — lowercase internal item name such as `electronic-circuit`.
- `optional-position-hint` — one of:
  - A `[gps=x,y,surface]` map ping from the player.
  - `view` for the current view center, including remote view.
  - `standing` for the physical character position.
  - `north`, `north-east`, `east`, `south-east`, `south`, `south-west`, `west`,
    or `north-west`, relative to the current view.
  - `view:<direction>` or `standing:<direction>` to preserve both the requested
    origin and directional sector.
  - Empty when the player supplied no location.

The classifier uses the pseudo-surface `current` when a player-relative request
does not name a surface. Phase 1 resolves it from `LuaPlayer.surface` for the
view or `LuaPlayer.physical_surface` for the physical character, and serializes
the real surface into its result for Phase 2.

The classifier prompt describes the format and current explicit-location limit:

```
- PRODUCE|surface|item|location — place a production cell for the requested item.
  Copy an explicit player-supplied GPS map ping exactly. Never invent or adjust
  coordinates. Normalize view, standing, the eight named directions, and
  origin-qualified directions such as standing:north. Use current when a
  relative request does not name a surface.
```

The current cell supports item-only recipes. Classification may still identify
a fluid recipe, but placement will return a grounded unsupported-fluid error
rather than ghosting a cell that cannot run.

## Parsing

A new `parse_produce_decision(raw)` function mirrors
`parse_logistics_decision`. It validates surface and item names with the same
internal-name rules (lowercase, digits, hyphens, underscores) and extracts the
optional structured location hint.

```python
def parse_produce_decision(raw):
    if not raw.startswith("PRODUCE|"):
        return None
    parts = raw.split("|")
    if len(parts) not in (3, 4):
        return None
    surface = parts[1].strip()
    item = parts[2].strip()
    hint = parts[3].strip() if len(parts) == 4 else ""
    if not valid_name(surface) or not valid_name(item):
        return None
    return surface, item, hint
```

The parser returns exactly `(surface, item, hint)`. Dispatch adds the requesting
player separately when calling `place_production_cell()`.

## RCON Logic

### Phase 1 — Resolve and verify a location (read-only)

The first Lua command validates bounded candidates without changing the world:

1. Resolve the requested surface. `current` means the connected player's viewed
   surface, except `standing` uses their physical surface. Resolve the recipe
   and reject fluid ingredients or products, locked recipes, and invalid recipe
   surface conditions.
2. Read every recipe category from `r.categories`. Use the live
   `crafting-category` entity-prototype filter to find compatible placeable
   assembling machines and furnaces, excluding unrelated fixed-recipe machines.
   Sort candidates by crafting speed, footprint, then name.
3. For explicit GPS, floor the coordinates to the bottom-left anchor tile.
   Otherwise choose the origin from the connected player's view, their physical
   position for `standing` or `standing:<direction>`, or the force's actual spawn
   on a named surface when an omitted location cannot use the player's view. A
   bare direction and `view:<direction>` both use the current view for backward
   compatibility. For each compatible
   machine, read `tile_width` and `tile_height`; generate deterministic expanding
   square rings in full-footprint steps normally and one-tile steps on Aquilo,
   filter to a named directional sector when requested, and stop at 128 tiles or
   256 anchors.
4. Compute the complete cell bounding box:
   - Left boundary: `anchor_x - 2`.
   - Right boundary: `anchor_x + w + 2`.
   - Bottom boundary: `anchor_y - 1`.
   - Top boundary: `anchor_y + h`.
5. For each candidate:
   a. Reject any entity or ghost in the complete bounding box.
   b. Preflight every planned entity with `can_place_entity()` and
      `script_ghost`.
   c. Check logistic coverage at the requester and construction coverage at
      every planned entity.
   d. Check whether the planned normal-quality medium pole's supply area covers
      the building center.
   e. Prefer a direct mutual-wire-reach connection to an existing powered pole,
      or breadth-first search half-tile pole centers for at most two extension
      poles. Every extension candidate must be outside the complete cell box,
      unoccupied, placeable as a ghost, and in construction coverage.
   f. On Aquilo, inspect each planned prototype's live `heating_energy`. Chests
      and poles with zero heating demand need no heat; the building and each
      inserter independently need any part of their collision box adjacent,
      including diagonally, to a heat source whose live temperature is at least
      30°C. The whole building footprint does not need to touch heat. Try the
      five-entity heated-ring layout first and check existing powered-pole supply
      at its building and both inserters.
6. Return the first fully supported candidate. During the same search, remember
   the first candidate that passes occupancy and exact `can_place_entity()`
   checks. If no fully supported candidate exists, return that structural
   fallback marked for support warnings. Return a grounded failure only when no
   structurally placeable candidate exists.

The product item is never treated as the crafting machine merely because it has
a placeable entity prototype.

### Phase 2 — Place and verify (mutation)

A second Lua command repeats the mutable assumptions and then creates all ghosts
in one `pcall`:

1. Re-resolve the surface, player, recipe, building, and needed pole prototypes
   and require the building dimensions to still match Phase 1.
2. Repeat the complete bounding-box occupancy scan and every per-entity
   `can_place_entity()` check as hard requirements. Recheck logistic and
   construction coverage and selected-layout power. On Aquilo, recheck every
   freezable component's live heat adjacency, existing power for the compact
   machine and inserters, and ensure retained heat sources overlap no exact
   planned component. For the standard layout, recheck each extension position
   for occupancy and placement as hard requirements, plus construction coverage,
   pairwise wire reach, and a final live powered-pole connection. A strict
   candidate rolls back if support changed after Phase 1; a marked fallback
   records support and construction-registration deficiencies as warnings.
3. Create the building at `(x+w/2, y+h/2)`, the requester and provider at
   `(x-1.5, row)` and `(x+w+1.5, row)`, the two west-facing inserters at
   `(x-0.5, row)` and `(x+w+0.5, row)`, and the pole at
   `(x+floor(w/2)+0.5, y-0.5)`, where
   `row = y+floor(h/2)+0.5`, followed by the exact preflighted extension poles.
   For `aquilo-compact`, instead create the serialized five-entity ring geometry
   and no pole.
4. Verify that the building ghost retained the requested recipe.
5. Call `requester_ghost.copy_settings(building_ghost, player)` and verify that
   every recipe ingredient appears in its logistic sections with a positive
   `filter.min`.
6. Verify every new ghost with `is_registered_for_construction()`.
7. Print the GPS anchor, dimensions, recipe, exact entity list, and every support
   warning on success. On structural or settings failure, destroy the newly
   created ghosts in reverse order, count any survivors, and report an incomplete
   rollback explicitly.

The mutation call uses `retry=False`; an uncertain RCON failure is never replayed.

## Dispatch Block

The main loop gains a new block after the logistics block, following the
same pattern:

```python
if produce_request is not None:
    rcon_cmd = "RCON: production cell"
    try:
        rcon_response = place_production_cell(
            client, *produce_request[:3], requesting_player=username
        )
        print(f"PRODUCE response: {rcon_response}", flush=True)
    except Exception as e:
        print(f"RCON error: {e}", flush=True)
        rcon_response = f"[error: {e}]"
```

## Reply Prompt

The reply prompt gains a hint for production-cell results:

```python
produce_hint = ""
if rcon_command == "RCON: production cell":
    produce_hint = (
        "This response is the result of placing a production cell. "
        "Report the anchor position and the entities created. If it "
        "failed, say what went wrong.\n"
    )
```

## Implementation Order

### Step 1: `place_production_cell()` in `jimbo.py` — explicit location preflight

Implemented. The Phase 1 Lua command is built by Python and run read-only through
RCON. It validates one explicit GPS anchor and returns an anchor, dimensions,
and compatible building prototype or a grounded failure string.

### Step 2: `place_production_cell()` — placement and verification

Implemented. The Phase 2 Lua command repeats preflight, creates and verifies the
six base ghosts and any planned extension poles, and returns either a success
message with the anchor GPS link and entity summary or a failure description. It
does not retry mutation.

### Step 3: Parser and dispatch

Implemented. The parser returns only the three placement fields, the classifier
recognizes structured production-cell requests, dispatch supplies the requesting
player, and reply composition distinguishes verified success from grounded
failure.

### Step 4: Power extension subplan

Implemented with a bounded extension-only scope. The fixed cell pole must remain
in construction range and supply the building. If it cannot reach an existing
powered pole directly, Phase 1 breadth-first searches half-tile centers for at
most two medium-pole extensions using the live normal-quality wire distance.
Phase 2 revalidates the exact chain and creates every pole in the same `pcall`
and rollback list. Shifting the cell or fixed pole remains deferred.

### Step 5: Bounded automatic and player-relative location search

Implemented. Explicit GPS remains exact. `view` uses the current controller
position and surface, so it follows remote view; `standing` uses the physical
controller position and surface. `view:<direction>` and
`standing:<direction>` preserve the chosen origin while filtering the requested
sector. Bare directions remain current-view-relative for compatibility. An
omitted hint uses the online player's matching view, otherwise the requested
surface's force spawn. The deterministic expanding-ring search uses full-cell
footprint steps and is bounded to 128 tiles and 256 anchors per compatible
machine. Aquilo uses one-tile steps so a prebuilt heat ring is not skipped by
the coarser standard grid.

### Aquilo heat refinement

Implemented after Step 5. The blanket Aquilo rejection is gone. Phase 1 and
Phase 2 use live prototype collision boxes, `heating_energy`, source
`heating_radius`, and source temperature. Any overlap with the radius counts, so
one adjacent building cell is sufficient; inserters are checked independently,
while zero-demand chests and poles are exempt. Heat sources may remain in unused
space inside the outer cell rectangle, but exact component overlap is still
rejected before `can_place_entity()`. Jimbo first tries a compact ring layout
with the machine at the north/top, two chests along the south/bottom, and their
inserters between them. It adds no pole there; the machine and both inserters
prefer existing live electric coverage, with a warning when a structural
fallback lacks it.

### Step 6: Prototype resolution caching and refinement

The placement function already resolves compatible machines from every live
recipe category and queries each candidate's tile dimensions during Phase 1. A
later refinement may cache this prototype information within one server session
or introduce an explicit machine-selection policy. Refetch it after a server
restart because mods or game updates may change the prototypes.

## Safety Constraints

- Every entity position is preflighted with `can_place_entity()` before any
  ghost is created.
- The full bounding box is scanned in both phases because `script_ghost`
  placement checks alone can accept some infrastructure overlaps.
- Logistic and construction coverage are preferred. If the bounded search finds
  no fully supported candidate, their absence is reported on the successfully
  placed structural fallback.
- Fluid recipes are rejected because neither current layout has pipe
  connections.
- On Aquilo, both phases check whether every component with nonzero prototype
  `heating_energy` touches an existing heat source at 30°C or warmer. Missing
  heat is reported on a structural fallback; exact overlap with a heat source
  remains a hard rejection. Heat sources may remain inside unused portions of
  the outer rectangle.
- The entire mutation is wrapped in `pcall`; on failure all new ghosts are
  destroyed in reverse order, survivors are counted, and no success is printed.
- Settings verification (`copy_settings` + section inspection) happens in
  the same RCON command to catch fulfillment races.
- Building dimensions are queried from live prototypes, never hardcoded.
- Power validation applies quality-aware supply and wire distances and searches
  pairwise-reachable chains of at most two extension poles ending at an existing
  live network. Missing live power is a fallback warning; an extension position
  that is occupied or cannot accept its ghost remains a hard failure.
- Never replay a mutation automatically after an RCON disconnect.

## Failure Modes

| Condition | Behavior |
|---|---|
| Surface does not exist | Return error; no mutation |
| Recipe not found, locked, or invalid for the surface | Return error; no mutation |
| Recipe has a fluid ingredient or product | Return unsupported error; no mutation |
| Aquilo candidate lacks ≥30°C heat adjacency for a freezable component | Keep searching; if no fully supported site exists, place the structural fallback and warn |
| Retained heat source overlaps an exact planned component | Reject the candidate; no mutation |
| No compatible placeable crafting machine | Return error; no mutation |
| Explicit GPS is invalid or names another surface | Return error; no RCON or mutation |
| `view`, `standing`, direction, or `current` needs an offline player | Return grounded error; no mutation |
| Omitted location and no matching online view | Search from the requested surface's force spawn |
| Automatic search exhausts 128 tiles or 256 anchors | Return the last grounded candidate failure; no mutation |
| Occupancy or any `can_place_entity()` check fails | Reject the candidate; no mutation |
| Logistic or full-cell construction coverage is absent | Keep searching; if needed, place the structural fallback and warn |
| Planned pole cannot supply the building | Keep searching; if needed, place the structural fallback and warn |
| No direct or at-most-two-pole route to live power | Keep searching; if needed, place the structural fallback and warn |
| Extension position becomes occupied, unplaceable, or exceeds pairwise wire reach | Roll back every new ghost |
| Extension loses construction coverage or its final live-power connection | Strict candidate rolls back; structural fallback places and warns |
| `pcall` catches an error during mutation | Destroy all newly created ghosts in reverse order; return error |
| A newly created ghost survives rollback | Report the original error and the survivor count |
| `copy_settings` does not produce expected requester filters | Destroy all ghosts; return error |
| Construction registration fails for any ghost | Strict candidate rolls back; structural fallback places and warns |
| RCON disconnect during Phase 2 | Report failure; do not replay |
| Requesting player missing | Reject before mutation because recipe-copy settings require that player |

## Testing

The deterministic `ProduceCellTests` in `test_jimbo.py` cover:

- classifier instructions, origin-qualified direction parsing and rejection,
  backward-compatible view-relative directions, three-field dispatch with the
  requesting player, and grounded reply guidance;
- strict GPS validation, surface matching, flooring, required-player behavior,
  malformed Phase 1 responses, remote-view versus physical-position origins,
  resolved-current-surface transfer, spawn fallback, direction filtering, and
  the radius/candidate bounds;
- live category-based machine resolution, dimensions, half-tile geometry,
  inserter directions, fluid/surface-condition rejection, Aquilo heat checks and
  source-overlap handling, power, logistics, construction coverage, strict-site
  preference, warning fallback, and both-phase placement checks;
- bounded extension search, strict serialized-chain validation, Phase 2
  extension rechecks, and extension ghost creation;
- creation of all base and extension ghosts, recipe and requester-filter
  verification, construction registration, occupancy-race rejection, reverse
  rollback with survivor reporting, and disabled mutation retry.

## Rollback

The current mutating command stores each successfully created ghost object in a
cleanup list. On any failure within the `pcall`:

1. Iterate the stored list.
2. Destroy each still-valid newly created ghost in reverse creation order,
   isolating individual destruction failures.
3. Count any still-valid survivors.
4. Return the original mutation error and, when nonzero, the survivor count.

Independently verifying a successful mutation in a later read-only command
remains deferred. The mutation is not automatically replayed after an uncertain
RCON disconnect.
