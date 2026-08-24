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

- **Step 1 - Parameterized layouts.** Lift cell shapes out of the monolithic
  Lua string into Python-side entity tables plus declared knobs (rotation,
  lanes-per-side, belt-vs-chest input/output, machine tier). Code keeps all
  geometry validation; the classifier picks knob values within ranges. First
  customer: a `belt-fed` cell modeled on the owner's hand-built example near
  nauvis [gps=13,7]: machine between parallel east-flowing belt lanes,
  long-handed inserter tapping input off one lane, inserter dropping output to
  the other, no chests. Rotation and lane count are knobs decided during
  implementation, not owner pre-decisions. Ship the reply-prompt honesty rule
  (report only what the RCON response literally says) together with this step.
  Contracts + announcement required.
- **Step 2 - Worker subprocess for open-ended requests.** Hard requests fork a
  short-lived process holding sliced runtime-API docs, the layout compiler,
  deterministic validators (inserter reach <=2, footprint overlap, belt
  connectivity, pole power reach), and read-only RCON site survey (water,
  cliffs, neighbors). Generate-validate loop on a time/iteration budget, one
  worker at a time. Only validated plans stamp, and only through the existing
  phase-2 path. Chat gets an immediate ack and a completion message.
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

Items 1, 2, 4, and 5 shipped 2026-08-23 (sections deleted per the merge
rule). Next: item 3 Step 1; item 6 remains deferred.
