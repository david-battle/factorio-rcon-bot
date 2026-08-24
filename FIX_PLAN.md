# Failure-Mode Fix Plan

Working plan from 2026-08-23 chat debugging. Work items one at a time; each
item below is self-contained enough to execute from its section alone. Delete
an item's section once merged. Items marked [decision] need an owner choice
before coding. Any item that changes player-visible behavior (code or prompt)
must update `startup_change_summary` and append its exact text to
`STARTUP_ANNOUNCEMENTS.md` in the same edit. Validate every Python change with
`python -m py_compile` plus the deterministic tests in Operations.

Shipped 2026-08-23 (sections deleted per the merge rule): lookup slash-prefix
normalization, ghost-check idiom in the scripting reference, classifier
LOOKUP recognition, and the REMOVE entity-removal verb.

## 3. PRODUCE grows beyond one pre-planned cell shape

Evidence: 17:37:17 Koopix asked for belt-fed/no-logistics; Jimbo replied
"This one skips the logistics chests entirely" while the RCON response in the
same log shows requester-chest + passive-provider-chest placed again. The cell
template had exactly one player-facing shape; the model invented a variant and
contradicted ground truth present in its own context.

Decision (owner, 2026-08-23): build real variant capability, working toward
on-demand layout synthesis rather than a refusal path. Reference material only
(not authoritative, never copied blindly):
`/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints` — Python blueprint
generators (`qup/cell.py` builder style) whose generate-validate-test loop is
the pattern to bring request-time.

Roadmap, one shippable step at a time:

- **Step 1 - Parameterized layouts. SHIPPED 2026-08-23.** Cell shapes now
  live as Python entity-offset tables (`standard`, `aquilo-compact`,
  `belt-fed`) instantiated per live machine footprint and serialized into
  both phases; the classifier picks enumerated knobs
  (`layout`/`rotation`/`lanes`/`tier`) validated in Python. The belt-fed
  cell (machine between two east-flowing lanes, long-handed input tap,
  regular output drop, no chests, walkway power pole) shipped together with
  the reply-prompt honesty rule and live placement verification. Furnace
  ghosts cannot carry preset recipes, so furnace cells place with an
  inherent "set recipe by hand" warning.
- **Step 2 - Worker subprocess for open-ended requests. SHIPPED AND
  LIVE-VALIDATED 2026-08-24 (205 tests pass; Jimbo restarted with it).**
  Live: a `layout=custom` copper-cable request spawned a detached worker
  (PID tracked, no RCON), a concurrent free-form belt-fed placement ran
  independently without deduping against it, `JOBSTATUS` answered from stored
  state across three checks, and the worker's accepted 2-iteration design was
  re-validated, normalized, stamped via Phase 2, and reported truthfully
  (status `done_placed`, `reported=true`, worker exited cleanly). The produced
  design was functional but basic (assembling-machine-1, a 2-belt tail) — a
  quality/optimization concern, not a scaffolding defect; see
  `FUTURE_DIRECTIONS` direction 14.

  Trigger (both paths, owner decision 2026-08-24):

  - Classifier: `layout=custom` joins the documented knob range. The model
    picks it when the player asks for a shape no pre-planned variant covers;
    Python validates it like any other knob value.
  - Python fallback: the requested pre-planned variant exhausts every bounded
    anchor with no structurally placeable candidate (Phase 1 structural
    failure — not a support fallback, which already succeeds on its own).

  Duplicate suppression: while a job for the same surface + item + rounded
  origin is pending or running, new triggers reply with job status instead of
  spawning another worker.

  Architecture:

  - The parent gathers all server facts read-only before forking: the
    existing candidate probe (compatible machines and tile dimensions), an
    occupancy/entity survey over the bounded search region (entities by name,
    position, dimensions; water and cliff coverage), live pole supply/wire
    distances, and recipe ingredients/products. The worker itself has no RCON
    connection.
  - Parent forks one short-lived worker: `python jimbo.py --produce-worker
    <job.json>`. The job file carries the player's ask, dialogue context
    excerpt, survey facts, prototype facts, validator constants, and budgets.
  - Loop: the model returns one complete entity-offset table per iteration in
    the exact schema Step 1 already stamps (`n/x/y/d/r` entries plus area).
    Python validates deterministically before accepting anything: schema and
    prototype existence against surveyed facts; pairwise footprint overlap
    from live dimensions; each inserter's pickup/drop target tiles exist at
    measured reach distances (regular 1.00/1.20, long-handed 2.00/2.20); belt
    lanes connect end to end and reach their inserter targets; a pole's
    supply distance covers the machine center; nothing exceeds the declared
    area. Validation failures return verbatim to the model as the next
    iteration's input. First valid table wins.
  - Budgets (owner decision 2026-08-24): hard stop at one hour wall clock,
    plus a 15-iteration runaway cap. On exhaustion the worker writes a
    grounded failure result and exits nonzero.
  - One worker at a time. Jobs live under gitignored `produce_jobs/<id>/`
    (input json, log tail, result json) so a Jimbo restart can report
    finished results and reap stale jobs.

  Stamping and chat flow (shape approved by owner 2026-08-24):

  - The parent independently re-validates the winning table (defense in
    depth), runs a custom-plan Phase 1 ring search for a free anchor, then
    stamps through the EXISTING Phase 2 mutation path with the table
    embedded. The chat model still never places geometry directly, and the
    mutation stays all-or-nothing with full rollback.
  - Chat gets one immediate acknowledgment line, then exactly one completion
    message applying today's verified-success/failure honesty rules.
    Follow-ups such as "how's it going" read pending-job status instead of
    triggering anything.

  Requires BOT_CONTRACTS updates (custom knob, async ack/completion, job
  status) and a startup announcement in the same edit.
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

Items 1, 2, 4, and 5 shipped 2026-08-23, and item 3 Step 1 shipped the same
day (with furnace-warning corrections 2026-08-24). Item 3 Step 2 (custom-cell
worker subprocess) shipped and was live-validated 2026-08-24. Item 3 Step 3
(verified primitive library) is the natural next step. Item 6
(tech-level-aware placement) stays deferred until item 3 lands.
