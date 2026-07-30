# Handoff

## Verified State

- Branch: `main`. HEAD before the handoff commit is `5d346a9`
  (`Document grounded calculation feedback`), equal to `origin/main`.
- Jimbo is running as the sole `python -u jimbo.py` process, PID `251668`,
  started 2026-07-29 18:12:16 local time. It uses the centrally selected
  `openai/gpt-5.4-mini` profile.
- The running process loaded the current code changes. Its startup announcement
  was observed at 18:12:04:
  “I no longer silently drop messages that directly address me, and
  production-cell searches now record why candidate sites were rejected.”
- `AGENTS.md` is authoritative. Read `OPERATIONS.md` for runtime procedures,
  `PROD_CELL_PLACE.md` for the production-cell contract, and
  `FUTURE_DIRECTIONS.md` before implementing behavior from the live findings.
- `last_chat_review.txt` was advanced through 2026-07-29 23:32:09. It is
  intentionally ignored and is not part of the commit.

## Completed Work

### Production-cell reliability

- Origin-qualified directions preserve both meanings of “current location”:
  `standing:<direction>` starts from the physical character, while
  `view:<direction>` starts from the current map view. Bare directions remain
  view-relative for compatibility.
- Phase 1 still searches deterministic bounded rings from the selected origin.
  It now prefers full heat, power, logistics, and construction support but
  remembers the first structurally placeable fallback.
- If no fully supported site exists, Phase 2 may place that structural fallback
  and returns every missing support condition as a warning. Occupancy, exact
  placement, recipe/settings verification, non-retried mutation, and rollback
  remain hard requirements.
- Every completed Phase 1 search emits a private `TRACE` payload. Python strips
  it from reply context and writes a compact `PRODUCE search trace` line to
  `jimbo.log`, including origin, direction, candidate counts, rejection/support
  counts, and the selected strict/fallback anchor.

### No silent direct failures

- A standalone case-insensitive `Jimbo` word marks the current message as
  directly addressed.
- A classifier `SKIP` on such a message is retried once with a corrective
  prompt. A second `SKIP`, classification exception, failed or empty RCON,
  reply-composition error or `SKIP`, empty filtered reply, or delivery failure
  receives the deterministic request-failure acknowledgment when delivery is
  still possible.
- Unaddressed intentional `SKIP` decisions remain silent. Mutations still need a
  nonempty executable command and printed verified result.

### Durable live findings

`FUTURE_DIRECTIONS.md` now records:

- the requested future alert monitor and the transient
  `no_platform_storage` alert observed during orbital request allocation;
- the likely but unconfirmed stale platform-request allocation after hub
  auto-trash freed space, plus the successful delete/recreate workaround;
- complete asteroid accounting through collectors, belts, hub, inserter hands,
  crusher inputs/outputs/in-crafting contents, crusher byproducts, hold versus
  pulse signals, and remaining same-tick race behavior;
- unsupported “remember/save this GPS” behavior after Jimbo falsely claimed it
  had durably saved a location;
- Factorio 2.1 electric-network diagnosis using every
  `LuaEntity.electric_networks` entry, switch copper connectors, live flow, and
  the historical-statistics trap;
- grounded Aquilo solar, fixed drain, power-switch, latch, and roboport buffer
  findings.

## Live Validation

- At 18:14:28, `standing:north` selected strict compact anchor
  `[gps=-30,-8,aquilo]` after 43 searched anchors. Jimbo placed and verified the
  iron-gear-wheel cell and reported it at 18:14:45.
- At 18:20:25, the same path selected strict compact anchor
  `[gps=-34,-9,aquilo]` and placed the electronic-circuit cell with an
  electromagnetic plant.
- At 19:30:09, it selected strict compact anchor
  `[gps=-38,-9,aquilo]` and placed the copper-cable cell. All three searches
  produced the new diagnostic trace.
- Later direct assistant RCON work was read-only. No game entities, wiring,
  requests, recipes, or circuit settings were changed during the side quests.

## Aquilo Power Diagnosis

During the user's reported problem, the open switch at
`[gps=-16,-9,aquilo]` cleanly separated the grids:

- electric subnetwork `3130` contained all 338 normal solar panels and no
  turbine;
- electric subnetwork `3661` contained both steam turbines and no solar panel;
- no producer reported multiple live network IDs and no hidden copper bridge
  crossed the open switch.

Each side's flow-statistics table still contained a zero-valued historical key
for the other generator type. The apparent solar panel on the steam side and
turbine on the solar side were therefore historical GUI entries, not current
connections at that moment.

The save changed again while this handoff was being written. The final
read-only check found the switch closed, 215 panels on subnetwork `3130`, five
turbines on `3130`, and two turbines on subnetwork `3662`. A closed switch can
join distinct subnetworks through one parent electric network, so compare both
subnetwork IDs and `parent_network.sub_networks`. Requery instead of relying on
either snapshot; players are actively rebuilding Aquilo.

## Validation

- `python -m py_compile jimbo.py test_jimbo.py`
- `python -m unittest test_jimbo` — 93 deterministic tests pass.
- Live production-cell traces and verified placements listed above.
- Read-only `LuaEntity.electric_networks`, switch-connector, pole-wire, and
  `flow_last_tick` inspection of both Aquilo grids.
- `git diff --check`

## Remaining Work

- No new implementation is authorized. Await the user's next request.
- The highest-priority previously identified behavior remains a small grounded
  quantitative-mechanics path; do not leave rates, capacities, recipe
  requirements, or timings to free-form `NONE`.
- Alert monitoring, platform-request diagnosis, asteroid circuit auditing, and
  durable GPS bookmarks are documented future possibilities, not implemented
  Jimbo features.
- If structural production-cell fallbacks need tuning, use the recorded search
  traces to distinguish collision failures from missing heat, power, logistics,
  or construction support before changing search geometry.

## Operational Caveats

- Do not restart Jimbo or Factorio merely to resume work. Verify the existing
  process and logs first; use the detached procedure in `OPERATIONS.md` only
  when a restart is required.
- Any code change that will restart Jimbo must update
  `startup_change_summary` and append its exact text to
  `STARTUP_ANNOUNCEMENTS.md`.
- Never retry a production-cell Phase 2 mutation after an uncertain RCON
  disconnect.
- Electric-network GUI history is not live topology. Inspect
  `electric_networks`, current switch connectors, and current flow.
- Do not run live `test_ollama.py` while the Factorio client is using the GPU.
- Credentials, logs, PID/state files, player data, and local caches are ignored
  and must not be staged.

## Natural Next Action

No task is pending beyond this handoff. Start from the user's next request,
verify the runtime and save state before acting, and consult the relevant tested
finding rather than reconstructing it from chat history.
