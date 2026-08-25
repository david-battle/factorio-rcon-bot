# Future Directions

Jimbo should become more aware of what is happening across the server without
turning into a noisy monitoring system or requiring players to memorize exact
commands. These are ideas to explore, not committed implementation plans. Any
work should preserve the bot's simple architecture and favor useful context,
natural interaction, and restrained behavior.

1. **Refine shared conversational context.** The first bounded server-wide
   dialogue is implemented: 12 turns, 40 minutes, about 4,000 characters, Jimbo's
   delivered replies, relevant RCON facts, and restart hydration. Future work
   should tune those limits only from observed chat and consider richer context
   only when a concrete failure remains. See `docs/BOT_CONTRACTS.md` for
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

   A concrete player request from 2026-07-29 is for Jimbo to monitor important
   Factorio alerts. Query alerts through the live API, deduplicate them by type
   and target, and comment only when they remain actionable long enough to avoid
   chat spam. Verify the underlying condition before speaking when possible.
   Factorio 2.1.12 can briefly report `no_platform_storage` while orbital
   requests are being allocated even when the hub has usable space and delivery
   proceeds, so that alert specifically needs a short debounce plus live hub,
   request, and pending-delivery context rather than immediate repetition.

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

   A related live example was `Jimbo note this location. [gps=...]`: the
   no-RCON reply claimed that the location was saved for later even though Jimbo
   has no durable bookmark feature. Treat requests to remember, save, or mark a
   location as unsupported until a verified storage action exists; bounded
   dialogue context is not a persistent bookmark.

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

10. **Achievements-active mode.** Accepting any Lua console command disables map
    achievements for that session, and Jimbo now touches Lua constantly: every
    chat line (custom-sound delivery), research/alerts/platform/logistics
    queries, tagging, production cells, and console priming. A future optional
    mode could keep a save achievement-eligible by restricting Jimbo to plain,
    non-Lua RCON only — raw chat text with the standard ding instead of
    `game.forces.player.print`, built-in slash commands such as `/players` or
    `/evolution`, and none of the Lua-backed behaviors above. Classifier paths
    and prompt contracts would need a matching degraded set, and requests
    needing unavailable Lua facts should get a grounded decline rather than a
    guess.

11. **Version-exact Lua/RCON fluency (two-layer model-facing reference).**
    Jimbo's models were trained before Factorio 2.1 and compose freeform Lua
    from stale knowledge. Today only scattered prompt hints (the built-in slash
    list, one `prototypes.recipe` line) arm the classifier's `/`-passthrough,
    while all reliable behavior comes from Python-authored Lua in `jimbo.py`.
    The fix is not more piecemeal notes: the authoritative, version-exact
    reference already exists as machine-readable JSON shipped inside every full
    install — `/mnt/d/factorio-standalone/current/doc-html/runtime-api.json`
    reported `application_version` 2.1.16, matching the live server, alongside
    `prototype-api.json`. Sizes forbid wholesale injection: full runtime JSON
    is about 2 MB (~500K tokens), signatures-only about 0.64 MB; a single class
    slice is 2–40 KB, so delivery must be layered.

    **Layer 1 — generated essentials block (always available).** A small repo
    script parses the local `runtime-api.json` and emits a compact reference
    (target 3–6 KB): global objects, `/silent-command` single-line idiom with
    `rcon.print()` output and the ~4 KB response cap, the pcall-or-die rule,
    empty-response-is-not-success, common 2.x renames (`game.recipe_prototypes`
    → `prototypes.recipe`, item prototypes under `prototypes.item`, inventory
    `get_contents()` shape), plus distilled traps from `docs/RCON_NOTES.md`.
    Inject it into classification prompts (where Lua is authored) but keep
    greetings and spontaneous prompts lean to protect reply latency. Regenerate
    after every game upgrade as part of the documented upgrade procedure;
    commit the generated text, never the source JSON.

    **Layer 2 — on-demand class/concept retrieval.** Add a structured
    classifier decision such as `LOOKUP|class-a,class-b|question`: Python
    extracts the named slices from `runtime-api.json` (and `prototype-api.json`
    for prototype properties) — signatures plus truncated descriptions, capped
    around 12–16 KB — into one dedicated read-only Lua composition call, then
    executes and answers from its verified result like any other RCON path.
    This keeps novel introspection accurate for anything the API exposes at a
    cost of one extra model call on rare queries only.

    **Capability goals this must preserve.** Players may ask for anything they
    could find legitimately with enough in-game work. Target examples:
    "where are all the iron plates being carried off by bots going" and "which
    platforms regularly deliver science packs from Gleba". Both require
    discovering exact members at query time (robot cargo fields, platform hub
    logistic sections and import filters, flow statistics) rather than trusting
    memory — exactly what Layer 2 exists for.

    **Boundaries.** Guiding philosophy: Jimbo should feel frictionless.
    Restrictions exist only where unlimited help would drain the game of
    meaning, and even there the soft anti-cheat decline is an in-character
    nudge for players who want effort to matter — not a wall. When the two
    failure modes conflict, err on the side of frictionless. Ghost and
    blueprint placement sits firmly on the frictionless side: players already
    place arbitrary blueprints by hand, construction robots still demand real
    materials, and expansion of placement capability is wanted (see directions
    8 and 9). Reference prompts must state explicitly that placing ghosts or
    delivering blueprints is ordinary convenience — never declined, never
    treated as a mutation concern. Freeform Layer 2 composition therefore
    rejects only two narrow things: overt progression bypasses (spawning or
    granting items or equipment into inventories, teleporting players), which
    get the light in-character decline described in `docs/BOT_CONTRACTS.md`,
    and accidentally destructive one-liners (mass destroy/clear style calls),
    which are a reliability guardrail against hallucinated commands rather
    than policy.     Everything else — reading any state, creating ghosts,
    tagging, wiring queries — composes freely. Composed placement should still
    graduate over time to the verified staging, preflight, and rollback
    pipelines for reporting quality, not permission. Keep single-command Lua
    within the profile completion-token budgets by favoring compact semicolon
    style.

    **Status.** Layer 1 shipped 2026-08-23: `generate_lua_reference.py`
    builds `lua_essentials.txt` (~6 KB: global objects, global functions,
    full class index, core abort-rules) from the installed game's
    `doc-html/runtime-api.json`, and `jimbo.py` injects it into classification
    prompts only; regeneration is step 9 of the documented upgrade procedure.
    First live tests produced correct composed queries (a technology listing)
    and a working freeform entity-ghost     placement — but that command printed
    success without checking `create_entity`'s return value, which is exactly
    the unverified-reporting gap Layer 2's report-only-what-you-read
    discipline closes.

    Layer 2 shipped the same day: `parse_lookup_decision`,
    `extract_api_slices` (budget-capped slices from `runtime-api.json`),
    `build_lookup_prompt` / `compose_lookup_command`, the
    `forbidden_lua_reason` guardrail, and the `RCON: scripted lookup`
    dispatch with its verified-reporting reply hint.

    **Known gap (2026-08-23 live test).** "How many iron plates total exist
    on Nauvis?" correctly routed to LOOKUP with a well-composed question, but
    the compose step returned empty — Jimbo honestly replied `[error: model
    returned no command]`. No command ran, so `jimbo_commands.log` logged
    nothing, and there is no raw fallback telling us whether the model gave an
    empty reply, malformed fences, or a transient API failure. Two small
    follow-ups: (1) on an empty compose, log the raw `ask_ai` output or do a
    single light retry instead of a bare error; (2) write a compose-side audit
    entry (question + reason/raw) even on failure so the audit trail explains
    why a lookup came up empty.

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

12. **Request-time layout synthesis.** Extend PRODUCE from one pre-planned
    cell shape toward on-demand layouts: parameterized entity tables with
    declared knobs (rotation, lanes-per-side, belt-vs-chest input and output),
    then a short-lived worker subprocess that composes and validates plans
    offline against read-only site surveys. Per the 2026-08-25 owner replan,
    the goal is NOT to port the old repo's finished cells (qup/solar-chunk/
    display-panel-array); it is to give Jimbo the old repo's PLANNING TOOLING
    so he composes new layouts from scratch with no reference to old plan
    outputs. That tooling lives on as: the AI+validation worker loop, a
    deterministic throughput/balance tool (`layout_analysis.py`), and a fixed
    role vocabulary of surveyed building prototypes. The chat model never
    places geometry directly; every plan must be an artifact of code that ran
    and passed checks, stamped only through the existing gated phase-2 path.
    The active step-by-step plan lives in `FIX_PLAN.md` item 3.
    Per the 2026-08-25 owner replan, the worker was pivoted from "model emits
    a static JSON blob" to "model AUTHORS a Python generator program that we
    run and iterate against" (`layout_helpers.py`, `run_layout_generator`) —
    the coding-agent loop. Because the design intent is the free-text player
    hint expressed as code, this is the mechanism that lets Jimbo design
    almost anything words can describe. Remaining breadth gap: the job framing
    is still item-centric (the candidate/machine survey targets an item);
    broadening the survey vocabulary to arbitrary designs is the next step.

13. **Belt-fed cells are a pre-bot capability.** The owner's stated purpose
    for the belt-fed layout is early-game use before logistics or
    construction networks exist: ghosts are hand-filled with items exactly
    like blueprint placement, no roboport required. Consequences to honor:
    missing logistic/construction coverage is an expected condition for this
    layout, not a defect, so support warnings should stay informative rather
    than alarming; the medium-electric-pole requirement assumes Electric
    Energy Distribution 1 research, so a small-pole variant (or poleless
    placement beside an existing line) may be wanted for truly earliest-game
    use; and any future belt-fed work should be validated the way pre-bot
    players would actually experience it — hand-building from ghosts — not
    only through bot-driven construction.

14. **Custom-cell worker design quality.** The Step 2 worker subprocess
    scaffolding is live and validated (FIX_PLAN item 3 Step 2): the first
    live `layout=custom` design was accepted on iteration 2, stamped, and
    reported. The produced cell was functional but minimal — it chose the
    base `assembling-machine-1` over the fastest unlocked machine and used a
    short 2-belt tail rather than a through-flowing lane pair. Future
    quality work (separate from scaffolding) could: steer the worker toward
    the fastest available compatible machine from the surveyed candidates;
    prefer longer, through-connected lanes that both feed and can be
    extended; and ask the validator/prompt to prefer a balanced inserter
    direction so input and output lanes run parallel as in the belt-fed
    variant. Any change here is a player-visible behavior change and must
    update `startup_change_summary` + `STARTUP_ANNOUNCEMENTS.md` and be
    re-validated live.
