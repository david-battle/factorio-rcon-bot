# Production Cell Placement

Place a self-contained crafting cell (building, requester chest, provider
chest, two inserters, power pole) at a verified location so construction bots
can build it. The model specifies what to make; local code handles geometry,
preflight, placement, and verification. The building type is determined at
runtime from the requested item's recipe prototype so different building
sizes (3×3 assemblers, 5×5 EM plants/foundries/cryoplants, etc.) work
without hardcoded dimensions.

## Cell Layout

The building's bottom-left tile is the anchor `(x, y)`. All other positions
are relative to the building's dimensions `(w, h)` queried at runtime from
`prototypes.recipe[item-name].products[1].name` → `prototypes.entity[entity-name].tile_width/tile_height`.

```
[Req] [In] [Building w×h] [Out] [Prov]
                    Power pole at (x + w//2 - 1, y - 1)
```

| Component | Position | Notes |
|---|---|---|
| Building | `(x, y)` to `(x+w-1, y+h-1)` | Anchor is building's bottom-left |
| Input inserter | `(x-1, y + h//2 - 1)` | Reaches building input slot, facing right |
| Requester chest | `(x-2, y + h//2 - 1)` | One tile left of inserter |
| Output inserter | `(x+w, y + h//2 - 1)` | Reaches building output slot, facing left |
| Provider chest | `(x+w+1, y + h//2 - 1)` | One tile right of inserter |
| Power pole | `(x + w//2 - 1, y-1)` | Below building center; may shift if blocked |

For a 3×3 building this produces the same positions as a hardcoded layout.
For a 5×5 EM plant the bounding box grows naturally and inserters still
reach because they target the building's edge tile, not its center.

Every position is preflighted with `can_place_entity()` before any ghost is
created. The full bounding box is a union of all component rectangles.

## Classifier Integration

The model returns a new structured line during classification:

```
PRODUCE|surface|item-name|optional-position-hint
```

- `surface` — lowercase internal surface name such as `nauvis` or `fulgora`.
- `item-name` — lowercase internal item name such as `processing-unit`.
- `optional-position-hint` — one of:
  - A `[gps=x,y,surface]` map ping from the player.
  - A cardinal-direction phrase like `north`, `south-east`, `east of me`,
    `north of current location`, etc. The model must first query the
    requesting player's position, then compute the offset and emit a
    concrete GPS hint. Resolution is handled by the model's classification
    step; the code only receives resolved GPS coordinates.
  - Empty if the player gave no location reference; Jimbo will search
    automatically.

The classifier prompt gains lines describing the format and directional
resolution:

```
- PRODUCE|surface|item|gps — place a production cell to craft the given item
  on the given surface. Use when someone asks Jimbo to make, produce, craft,
  build, or set up manufacturing of a specific item. Include the player's GPS
  ping as the position. If the player says a direction like "north of me",
  first run "/silent-command rcon.print(game.players[\"username\"].position)"
  to get their position, then compute the offset, and emit PRODUCE with a
  concrete [gps=...] location. Omit the hint to let Jimbo choose.
```

## Parsing

A new `parse_produce_decision(raw)` function mirrors
`parse_logistics_decision`. It validates surface and item names with the same
internal-name rules (lowercase, digits, hyphens, underscores) and extracts the
optional GPS hint.

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

## RCON Logic

### Phase 1 — Find and verify a location (read-only)

The first Lua command locates a buildable position. Building dimensions
`w` and `h` are queried first from the recipe → entity prototypes so
bounding boxes are correct for any building size:

1. Resolve the target surface and look up the building type/prototype
   dimensions for the requested item's recipe.
2. Compute the cell's total bounding box span:
   - Left edge: `anchor_x - 2` (requester chest)
   - Right edge: `anchor_x + w + 1` (provider chest)
   - Bottom edge: `anchor_y - 1` (power pole / inserters)
   - Top edge: `anchor_y + h - 1` (building top)
3. If the player gave a GPS hint, use that tile as the candidate anchor.
   Otherwise, find the online player who made the request, get their
   position, and search outward in a spiral for a clear area matching the
   computed bounding box.
4. For each anchor candidate:
   a. Scan `find_entities_filtered{area=...}` over the full bounding box
      for any entity or ghost — treat any occupancy as blocked.
   b. Preflight every planned entity position with `can_place_entity()`.
   c. Locate the nearest electric pole with a live network and verify the
      building falls within its quality-aware supply area.
   d. Verify the requester position has logistic coverage via
      `surface.find_logistic_network_by_position()`.
5. Return the first clear anchor and the building name, or report failure.

### Phase 2 — Place and verify (mutation)

A second Lua command creates all ghosts in one `pcall`. Positions use the
building dimensions `(w, h)` determined in Phase 1:

1. Create building ghost at anchor `(x, y)` with dimensions `(w, h)` and
   the requested recipe.
2. Create requester chest ghost at `(x-2, y + h//2 - 1)`.
3. Create passive provider chest ghost at `(x+w+1, y + h//2 - 1)`.
4. Create input inserter ghost at `(x-1, y + h//2 - 1)` facing right.
5. Create output inserter ghost at `(x+w, y + h//2 - 1)` facing left.
6. Create power pole ghost at `(x + w//2 - 1, y-1)`.
7. Call `requester_ghost.copy_settings(building_ghost, player)`.
8. Verify `requester_ghost.get_logistic_sections().sections` contains every
   recipe ingredient with a positive `filter.min`.
9. Verify each new ghost's construction registration with
   `is_registered_for_construction()`.
10. Print the anchor and entity list on success; on failure remove all newly
    created ghosts and print the error.

All entity lookups use `find_entities_filtered` with type + position, not
unit numbers, so positions work across RCON reconnects since we just placed
them.

## Dispatch Block

The main loop gains a new block after the logistics block, following the
same pattern:

```python
if produce_request is not None:
    rcon_cmd = "RCON: production cell"
    try:
        rcon_response = place_production_cell(
            client, *produce_request
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

### Step 1: `place_production_cell()` in `jimbo.py` — location search

Implement the Phase 1 Lua command as a pure Python function that builds and
runs the Lua string. Test with mocked RCON. The function returns either an
anchor `(x, y)` or a failure string.

### Step 2: `place_production_cell()` — placement and verification

Add the Phase 2 Lua command. Combine with Phase 1 so the caller gets one
response string: either a success message with the anchor GPS link or a
failure description.

### Step 3: Parser and dispatch

Add `parse_produce_decision()`, its entry in the classifier prompt, the
classifier `elif` branch, and the dispatch block. Wire the result into the
reply builder with the produce hint. The model can now request production
cells and Jimbo will reply with the outcome.

### Step 4: Power extension subplan

When the primary anchor has no electric coverage, search for the nearest
power pole in construction range, verify its supply area reaches a live
network, and include a medium-electric-pole ghost in the same `pcall`.
Track it for rollback.

### Step 5: Location spiral for player-free hints

If the player gives no GPS hint and the requesting player is offline, search
in an expanding outward spiral from spawn (0, 0) for a clear area with both
power and logistic coverage. The spiral step size adapts to the building's
bounding box dimensions.

### Step 6: Prototype lookup for building dimensions

The placement functions need the building entity's tile dimensions. Query
them at runtime:

```
/silent-command local r=prototypes.recipe["processing-unit"];local p=r.products[1];local e=prototypes.entity[p.name];rcon.print(e.tile_width..","..e.tile_height)
```

Cache the result in the local Python response; building dimensions for a
given entity name do not change during a server session but should be
refetched after server restarts.

## Safety Constraints

- Every entity position is preflighted with `can_place_entity()` before any
  ghost is created.
- Every new ghost occupies a unique tile; the bounding box scan rejects
  overlapping builds.
- The entire mutation is wrapped in `pcall`; on failure all new ghosts are
  destroyed and no claimed success is printed.
- Settings verification (`copy_settings` + section inspection) happens in
  the same RCON command to catch fulfillment races.
- Building dimensions are queried from live prototypes, never hardcoded.
- Power validation checks `pole.electric_network is not nil` and applies
  `pole.prototype.get_supply_area_distance(pole.quality)` to confirm the
  building is within supply radius.
- Logistic coverage uses `surface.find_logistic_network_by_position()` on
  the requester position.
- Never replay a mutation automatically after an RCON disconnect.
- Never use unit numbers from a previous RCON session to identify entities.

## Failure Modes

| Condition | Behavior |
|---|---|
| Surface does not exist | Return error; no mutation |
| Recipe not found or building cannot be determined | Return error; no mutation |
| No clear area found within search radius | Return "no suitable location"; no mutation |
| Any `can_place_entity()` fails during preflight | Skip anchor; try next candidate |
| `pcall` catches an error during mutation | Destroy all newly created ghosts; return error |
| `copy_settings` does not produce expected requester filters | Destroy all ghosts; return error |
| Construction registration fails for any ghost | Destroy all ghosts; return error |
| Power pole position is blocked (no alternate nearby) | Report location found but no power; skip anchor |
| RCON disconnect during Phase 2 | Report failure; do not replay |
| Requesting player is offline and no GPS hint given | Search from spawn; fail if no location found |

## Testing

Follow the deterministic test patterns in `test_jimbo.py`:

- **`test_parse_produce_decision_valid`** — valid `PRODUCE|nauvis|processing-unit|`
  and `PRODUCE|fulgora|holmium-plate|[gps=10,20,fulgora]`.
- **`test_parse_produce_decision_invalid`** — wrong prefix, missing fields,
  invalid item names.
- **`test_produce_location_search_finds_clear_area`** — mock RCON returns a
  clear area; verify correct Lua is built and anchor is returned.
- **`test_produce_location_search_blocked`** — mock RCON returns blocked;
  verify failure response.
- **`test_produce_placement_success`** — mock Phase 2 success; verify
  response contains anchor and entity summary.
- **`test_produce_placement_pcall_failure`** — mock Lua error; verify no
  entities are claimed and error is returned.
- **`test_produce_reply_hint_in_prompt`** — verify production hint text is
  injected into the reply prompt when rcon_command matches.

## Rollback

Every mutating command stores the list of newly created ghosts (entity
positions and types) before the mutation. On any failure within the `pcall`:

1. Iterate the stored list.
2. For each position, call `surface.create_entity{name="entity-ghost" ...}`
   only for entities that exist as ghosts — this is a no-op for already-built
   entities and safe.
3. Print the rollback result.

Rollback uses `find_entities_filtered{type="entity-ghost", area=...}` at
each stored position to confirm destruction. This runs inside the same
`pcall` so partial rollback also fails atomically.
