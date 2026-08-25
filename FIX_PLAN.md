# Failure-Mode Fix Plan

Working plan from 2026-08-23 chat debugging. Work items one at a time; each
item below is self-contained enough to execute from its section alone. Delete
an item's section once merged. Items marked [decision] need an owner choice
before coding. Any item that changes player-visible behavior (code or prompt)
must update `startup_change_summary` and append its exact text to
`STARTUP_ANNOUNCEMENTS.md` in the same edit. Validate every Python change with
`python -m py_compile` plus the deterministic tests in Operations.

Shipped and removed per the merge rule: items 1, 2, 4, 5, and item 3 Steps 1-2.
Their retrospectives are archived. Active items below: 3 Step 3, 6, 7, 8.

## 3. PRODUCE grows beyond one pre-planned cell shape

- **Step 3 - Verified primitive library.** Compose layouts from primitives
  that have each earned trust via tests (straight bus, tap-in inserter, chest
  drop, lane pair). Port candidates from the old repo: qup quality up-cycler,
  solar-chunk, display-panel array. Add a propose-then-confirm chat flow for
  large builds before stamping.
- **Later/optional - Sandbox prove-it mode**: stamp a disposable copy of a
  plan somewhere remote, watch it run, report, tear down. Largest lift;
  do not start before Steps 1-3 land.

Standing guardrails for every step: the chat model never places geometry
directly; every plan is an artifact of code that ran and passed checks;
BOT_CONTRACTS production-cell rules updated in the same edit as each visible
behavior change.

## 6. Tech-level-aware placement (known limitation)

Evidence: first PRODUCE placed an assembling-machine-3 into an early-game save
(17:35:29, Koopix's reaction; owner acknowledged 17:36:10). Placement ignores
researched technologies.

Deferred until item 3 lands unless reprioritized. Sketch: dispatch_production_cell
could query `game.forces.player.technologies` over RCON and pick the best
available assembling machine (and possibly chests) before stamping the cell.
Decide scope then; announcement required.

## Execution order

Item 3 Step 3 (verified primitive library) is the natural next step. Item 6
(tech-level-aware placement) stays deferred until item 3 lands.

## 7. `LuaInventory.get_item_count` rejects a quality argument

Evidence: 2026-08-25 04:34:58, Koopix asked Jimbo to count rare solar panels and
accumulators in containers across non-nauvis surfaces. The Lua
`inv.get_item_count("solar-panel","rare")` call failed with
`Arguments count error for 'get_item_count': Expected 0 or 1 arguments but 2
were given` (recorded in `jimbo_commands.log`). On Factorio 2.1
`get_item_count` does not take a quality parameter, contradicting the
OPERATIONS.md note that `LuaLogisticNetwork.get_contents()` returns
quality-aware entries — that API path is not universally mirrored by
`get_item_count`.

Fix: for quality-specific container counts, iterate `get_contents()` and sum
matching `name`/`quality` entries (as the earlier rare solar/accumulator query
already did on nauvis) instead of passing a quality argument to
`get_item_count`. Fold the finding into `docs/RCON_NOTES.md` in the same edit.

Dependency: none. Standalone RCON/Lua correctness fix, unrelated to items 3 or 6.

## 8. Map-tag placement fails on surface spawn coordinate lookup

Evidence: 2026-08-25 04:08-04:09, darklich14 asked Jimbo to set a map tag.
Jimbo's command referenced `game.surfaces["nauvis"].spawn_position` and then
`.spawn`; both errored ("LuaSurface doesn't contain key spawn_position/spawn").
Spawn coordinates are not a surface property in Factorio 2.1; they live on the
map settings, not the surface object.

Fix: read spawn coordinates from the map settings (or a reliable public API)
when placing a default-location map tag, and re-issue the tag. Update the
relevant prompt guidance so Jimbo stops guessing surface spawn keys. Add the
correct lookup to `docs/RCON_NOTES.md` in the same edit.

Dependency: none. Standalone RCON/Lua correctness fix, unrelated to items 3, 6,
and 7.
