# Handoff

## Verified State

- Branch: `main`. HEAD before this handoff documentation is `e0cb57a`
  (`Update production cell handoff`); use `git log -1` for the
  handoff commit created by the procedure.
- The tracked worktree was clean before this handoff. Local `main` was eight
  commits ahead of `origin/main`; nothing was pushed.
- Jimbo is running as the sole `python -u jimbo.py` process, PID `237127`,
  started 2026-07-29 16:50:59 local time. It uses the centrally selected
  `openai/gpt-5.4-mini` profile.
- The startup announcement was observed at 16:51:00. Its tracked summary is:
  “I can now fit Aquilo production cells inside compact heated rings, using the
  surrounding roboport and existing electric coverage instead of forcing my
  standard pole layout.”
- `AGENTS.md` is authoritative. Read `OPERATIONS.md` for runtime procedures,
  `PROD_CELL_PLACE.md` for the complete placement contract, and
  `FUTURE_DIRECTIONS.md` before extending behavior from live findings.

## Completed Work

Production-cell Steps 1 through 5 are implemented and reachable from chat:

- `PRODUCE|surface|item|location` supports exact GPS, current view, physical
  standing position, named directions, and bounded automatic search.
- Item-only compatible machines are resolved from live recipe categories and
  prototype dimensions. Fluid recipes remain deliberately unsupported.
- The standard six-ghost layout can add at most two fully preflighted extension
  poles to reach live power.
- Aquilo accepts existing heat infrastructure at 30°C or warmer, checks each
  freezable component independently, and rechecks heat before mutation.
- Aquilo first tries a five-ghost heated-ring layout: building at the north/top,
  inserters below it, requester and provider chests at the south/bottom, and no
  new pole when existing power covers the building and both inserters.
- Phase 2 remains `retry=False`, revalidates all mutable assumptions, verifies
  recipe, requester filters, and construction registration, and rolls back every
  newly created ghost on failure.

The commits after `origin/main` contain the completed rollout:

- `f6aeca7` hardens initial placement and contains OpenCode temp files.
- `921f2b5` records blueprint delivery findings.
- `fcd7b61` wires production cells into chat.
- `6288740` adds bounded power-extension poles.
- `af054bc` adds bounded/player-relative location search.
- `1c70b8f` adds live Aquilo heat validation.
- `39f09e9` adds the compact heated-ring layout.
- `e0cb57a` records the completed rollout and directional-origin limitation.

## Live Validation

- At 16:56:54, dlbattle repeated: “Jimbo please place a production cell for
  pump jacks north of my current location.”
- At 16:57:14, the running Jimbo reported verified success at
  `[gps=-21,-8,aquilo]` with an `assembling-machine-3`, requester chest, two
  inserters, and passive provider chest. The compact layout reused the existing
  substation; no cell pole was added.
- The user confirmed the blueprint appeared and began crafting the items needed
  to fill it. Other players also observed it in game.
- Earlier direct assistant RCON work was read-only or parse-only. The actual
  successful mutation was performed by the running Jimbo process.

## Player Feedback And Grounded Math

After the placement work, Jimbo improvised several quantitative mechanics
answers through `NONE` without RCON facts or calculations. It understated the
scrap needed for 1,000 electromagnetic science/min, understated normal silo
count for 3,000 scrap/min, and invented a one-second silo animation. Players
responded with “Do NOT trust AI” and “this one especially.” The correction was
accepted, but the durable issue is loss of trust from confident guessing.

`AGENTS.md` now requires quantitative and version-sensitive answers to use live
facts plus deterministic calculation or explicitly decline. `FUTURE_DIRECTIONS.md`
records the observed feedback, recommended calculation flow, and verified live
inputs:

- electromagnetic science requires magnetic field exactly 99 and is
  Fulgora-only;
- current bonuses imply roughly 78,000 scrap/min for 1,000 science/min before
  productivity modules;
- one rocket carries 500 scrap;
- 3,000 scrap/min means six launches/min and at least three fully supplied
  normal-quality silos at the animation-bound 26.9-second quick cycle.

Jimbo also misclassified an export-feasibility question as `PLATFORMS`; platform
names were irrelevant evidence. Raw Factorio chat displayed Markdown markers
literally. The last reviewed chat timestamp is 2026-07-29 17:18:32.

## Validation

- `python -m py_compile jimbo.py test_jimbo.py`
- `python -m unittest test_jimbo` — 83 deterministic tests pass.
- The exact Aquilo Phase 1 preflight returned
  `ANCHOR:-21,-8,3,3,assembling-machine-3,,aquilo,aquilo-compact`.
- Factorio parsed the full Phase 2 command and executed its complete preflight
  with creation disabled; the destination contained zero ghosts afterward.
- The later real chat request completed Phase 2 successfully as described above.
- `git diff --check`

## Remaining Work

### Grounded quantitative mechanics

The highest-priority behavioral refinement suggested by live feedback is a small
grounded path for quantitative recipe, cargo, throughput, surface-condition, and
timing questions. It should query only relevant prototype/live facts, calculate
locally, show controlling assumptions, distinguish theoretical minimum from
practical capacity, and decline unsupported calculations. Do not add a broad
knowledge framework or trust model-generated arithmetic.

### Directional origin semantics

Named directions currently always use the current view as their origin. The
single structured location field can encode either `standing` or `north`, but
not both. During the Aquilo test, the valid nook was north of the physical
character but west of the remote view, so `north` excluded it. Leaving map view
made the view and physical positions coincide and the same request succeeded.

If the user chooses to refine this, preserve both origin and direction with a
backward-compatible form such as `standing:north` and `view:north`. Update the
classifier, strict parser, Phase 1 surface/origin resolution, tests, and
`PROD_CELL_PLACE.md`. Do not silently redefine every existing direction without
considering requests that intentionally refer to remote view.

### Deliberately deferred

- Step 6 prototype caching or explicit machine-selection policy.
- Fluid-capable production-cell layouts.
- Shifting the fixed standard cell or pole layout when blocked.
- Independent read-only post-mutation verification.

## Operational Caveats

- Do not restart Jimbo or Factorio merely to resume work. Verify the PID and logs
  first; use the detached `nohup setsid` procedure in `OPERATIONS.md` only when a
  restart is actually required.
- Any code change that will restart Jimbo must update
  `startup_change_summary` and append its exact text to
  `STARTUP_ANNOUNCEMENTS.md` in the same edit.
- Never retry a production-cell mutation after an uncertain RCON disconnect.
- Do not run live `test_ollama.py` while the Factorio client is using the GPU.
- Credentials, logs, PID/state files, player data, and local caches are ignored
  and must not be staged.

## Natural Next Action

No task is currently authorized beyond this documentation handoff. Await the
user's next request. If they choose to address the player feedback, start with a
bounded grounded calculation path and deterministic fixtures for the failed
science/scrap/silo examples. The production-cell directional ambiguity remains
the next isolated placement refinement. Repeat deterministic and read-only live
validation before restarting Jimbo for either code change.
