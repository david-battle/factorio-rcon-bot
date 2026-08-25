# Failure-Mode Fix Plan

Working plan from 2026-08-23 chat debugging. Work items one at a time; each
item below is self-contained enough to execute from its section alone. Delete
an item's section once merged. Items marked [decision] need an owner choice
before coding. Any item that changes player-visible behavior (code or prompt)
must update `startup_change_summary` and append its exact text to
`STARTUP_ANNOUNCEMENTS.md` in the same edit. Validate every Python change with
`python -m py_compile` plus the deterministic tests in Operations.

Shipped and removed per the merge rule: items 1, 2, 4, 5, 7, 8, and item 3
  Steps 1-2. Their retrospectives are archived. Active items below: 3 Step 3, 6.

## 3. Jimbo generates composite layouts from scratch via planning tools

Replan 2026-08-25 (owner direction): do NOT port pre-planned cells from the
old repo (`qup`/`solar-chunk`/`display-panel-array`). Instead give Jimbo the
old repo's *planning tooling* — the analysis/search/validation tools AI used to
produce qup from scratch — so Jimbo composes new layouts of his own, with no
reference to old plan outputs. The old repo stays reference-only.

- **Step 3 - Generalize the custom-cell worker to multi-building composite
  layouts, plus a deterministic balance/throughput analysis tool.**
  - DONE (2026-08-25): schema/validator widened from exactly-one `building`
    to multiple `building` entries plus a broader vocabulary (`chest`,
    `splitter`, `underground-belt`, `combinator`, `recycler`/`foundry`/
    `chemical-plant` as buildings); entity cap 80→200, area cap 48→64. The
    anchor building (first entry) carries the recipe; other buildings place by
    name with no recipe. Pole coverage and inserter reach checks generalized
    to every building. `layout_analysis.py` (deterministic throughput/
    bottleneck tool) added and surfaced in the worker prompt.
  - DONE (2026-08-25): parent survey widened to a fixed role vocabulary —
    the item's crafting machines plus `custom_plan_support_buildings`
    (`recycler`, `foundry`, `chemical-plant`, furnace/assembler tiers)
    surveyed by type and merged into the `machines` facts.
  - DONE (2026-08-25): pivoted the worker from "model emits a static JSON
    blob" to "model AUTHORS a small Python generator program", which we run in
    the job's subdirectory and iterate against — the coding-agent loop.
    `build_custom_plan_prompt` now asks for a `generator.py` that computes the
    layout with `layout_helpers` and prints the plan dict to stdout;
    `run_layout_generator` executes it as a normal subprocess (owner chose NO
    restrictive sandbox — the code runs with Jimbo's own reach in the job
    dir; only its OUTPUT is gated by the deterministic validator). Runtime
    errors and validator rejections are fed back for the model to fix. Added
    `layout_helpers.py` (plan builders, reach, boxes, rotate) for generated
    code. This is the mechanism that lets Jimbo design "anything words can
    describe": the generator receives the free-text hint and expresses any
    build through code, within the validator's general geometric rules.
  - DONE (2026-08-25): parallel BANKS of identical machines are a first-class
    target. The recipe is now set on every building matching the plan's primary
    crafting machine (not the placement search's `en`), so a homogeneous bank
    gets its recipe on all machines; `layout_helpers.bank(facts, name, count,
    row_x, row_y)` builds a complete validator-ready bank (shared input belt
    -> one inserter per machine -> shared output belt -> pole per machine);
    the worker prompt guides the model to use banks for any volume ask. Bank
    geometry validated for 3x3..5x5 footprints across the support buildings.
  - FOLLOW-ON: the job framing is still item-centric (`query_production_cell_candidates`
    and the machine vocabulary survey a target item). Broaden to arbitrary
    designs: hint-driven survey vocabulary (allow other machine types), and
    keep the validator as-is (already geometry-general: overlap, reach, power,
    in-area, belt lanes). The code-authoring loop is in place; this broadens
    what it can survey/stamp.
  - FOLLOW-ON: mechanically invoke `layout_analysis` each worker iteration and
    feed per-proposal flow results/errors back (the proposal schema must first
    carry module/recipe flow inputs). The tool is in the prompt and importable
    by generators; deep loop wiring is next.
  - FOLLOW-ON: full quality-loop machinery (sorter, return belts, 15 item×
    quality routes) and the propose-then-confirm chat flow for large builds
    (Sandbox prove-it mode below).
- **Later/optional - Sandbox prove-it mode**: stamp a disposable copy of a
  plan somewhere remote, watch it run, report, tear down. Largest lift;
  do not start before Step 3 lands. Owner declined a hard runtime sandbox for
  generated code; prove-it mode (if built) is about observing a plan run, not
  restricting the generator.
- **Later - quality-loop machinery** (sorter, return belts, 15 item×quality
  routes): out of scope for the first generalized-worker landing; build
  incrementally after Step 3 representation + analysis land.

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
