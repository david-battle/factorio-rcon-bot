# Jimbo - Factorio RCON Bot

## Scope

This is a deliberately simple Factorio bot in `~/factorio-rcon-bot` on branch
`main`. It reads server activity, asks an AI model what to do, and uses RCON for
queries and chat replies. Do not add unrequested features or infrastructure such
as databases, web servers, or configuration frameworks.

Keep both the implementation and this always-loaded instruction file minimal.
Put infrequently needed setup steps, provider history, recovery procedures, and
other operational detail in `OPERATIONS.md`; keep only rules that future coding
contexts routinely need in `AGENTS.md`. Keep both files under roughly 8,000
combined tokens so local-model development remains practical.

## Required References

Read `OPERATIONS.md` before editing code. Also read it for environment setup,
RCON connectivity, provider/model changes, process management, testing, player
seeding, or runtime diagnosis.

Read `HANDOFF.md` when resuming work after a `/handoff`. Verify its status claims
against Git and the current files; `AGENTS.md` remains authoritative.

When asked to prepare or perform a handoff, follow `HANDOFF_PROCEDURE.md`.

Read `FUTURE_DIRECTIONS.md` before planning or implementing a new Jimbo feature
based on prior live experiments; tested implementation findings live there.

## Central Configuration

**Read this before changing owner, model, or provider behavior.** `jimbo.py` keeps
these project-specific choices in one top-level configuration block:

- `server_owner` is the only place the owner's username is configured.
- `ai_profile_name` is the only setting changed to switch the active AI model and
  its associated provider.
- `ai_profiles` contains the complete predefined `openai`, `deepseek`, `groq`,
  and `ollama` model/provider settings recovered from working project history.

Do not scatter owner names, model identifiers, provider names, endpoints, or
model-specific identity text through the code. Prompts and authorization checks
must derive them from the selected configuration. When adding or repairing a
profile, maintain its provider adapter, tests, and the profile reference in
`OPERATIONS.md`. Do not introduce a general configuration framework for this.

## Architecture

Keep three conceptual moving parts:

1. Server log input.
2. AI decisions and reply composition.
3. RCON queries/actions and chat output.

The development assistant operating this repository is not Jimbo. Direct RCON
work by the assistant may use the `Jimbo says ` prefix to format or impersonate
an in-game message, but must be reported as assistant action and never confused
with a decision or capability exercised by the running Jimbo process.

## Chat Listener

- Chat format: `YYYY-MM-DD HH:MM:SS [CHAT] username: message text`.
- Join/leave events use `[JOIN]` and `[LEAVE]`.
- Split on `[CHAT] ` before `: ` because timestamps contain colons.
- Ignore messages beginning with `Jimbo says ` to avoid processing bot echoes.
- `[JOIN]` triggers a model-generated greeting. `known_players.txt` determines
  whether the model is told that the player is new or returning.

## Request Flow

1. Parse a new chat line into username and message.
2. Ask the model for SKIP, NONE, PLATFORMS, PLANETS, structured LOGISTICS,
   structured PRODUCE, or a slash command.
3. Run canned platform, planet, logistic, or production-cell logic or the
   selected command if needed.
4. Ask the model to compose a short reply from the player message and RCON data.
5. Send each reply line separately as raw RCON text prefixed with `Jimbo says `.

The classifier defaults to SKIP unless the current message contains "Jimbo" so
the bot does not interrupt player-to-player chat. No-RCON replies may also SKIP.
Strip output lines beginning with `(Note:` or `(Corrected`.

Quantitative or version-sensitive mechanics answers must come from relevant live
RCON/prototype facts and explicit deterministic calculation. Do not use `NONE`
to improvise rates, capacities, recipe requirements, surface restrictions, or
timings. If the needed facts cannot be queried, say that the calculation is not
grounded rather than presenting an estimate as fact. An unrelated platform or
planet list is not evidence for the answer.

Logistic availability uses `LOGISTICS|surface|item-name,item-name`; `all` scans
every planetary surface. Keep results separated by surface and network, identify
silo-connected networks, and report nonnegative available stock. Availability is
not a recipe shortfall; compare it with exact requirements from dialogue. Do not
replace this path with ad hoc `LuaForce.logistic_networks` queries.

Production-cell placement uses `PRODUCE|surface|item-name|location`. Location
may be an explicit GPS ping, the current remote view, the physical character
position, a normalized direction, or an automatic bounded player/spawn search.
A fixed cell may add at most two fully preflighted extension poles to reach live
power. On Aquilo, every freezable component must touch a live heat source at
30°C or warmer; non-overlapping heat infrastructure may remain inside the cell's
outer rectangle. Preserve the verified non-retried mutation and complete
rollback contract in `PROD_CELL_PLACE.md`.

An explicit Jimbo request that objectively fails during classification, RCON,
reply composition, or delivery gets a short deterministic failure acknowledgment
when delivery remains possible. Intentional SKIP decisions stay silent.

A mutating request requires an executable nonempty command and a printed,
verified outcome. Treat a bare `/silent-command`, an empty RCON response, or an
unverified mutation as failure; never compose a success claim from it.

## Shared Dialogue Context

Jimbo keeps one server-wide conversation because Factorio chat is public. It is
bounded to the newest 12 logical turns, 15 minutes, and roughly 4,000 rendered
characters. It records player messages, successfully delivered Jimbo replies,
relevant spontaneous comments, and exact RCON facts associated with replies.

The current message is separate from history in prompts. History is background
only and must never revive an old request. Startup hydration reads recent player
and Jimbo chat without responding retroactively, filters startup and greeting
noise, and resumes tailing from the hydration endpoint so startup-time messages
are not lost. The forget meme clears both dialogue and spontaneous context.

Join greetings are intentionally excluded from dialogue. Successfully greeting a
player also resets the spontaneous timer so Jimbo does not welcome them twice.
Successfully delivered direct replies clear the accumulated spontaneous activity
because that conversation has been addressed, but remain in shared dialogue for
follow-ups.
Maintain these rules and the deterministic coverage in `test_jimbo.py` when
changing chat flow.

### Intentional Flexibility

The classifier may return any slash command, and the bot intentionally passes it
through to RCON. Do not add a command whitelist unless explicitly requested.
Occasional joking claims that an action is underway without RCON execution are
part of Jimbo's humor and do not need guardrails.

## Startup Announcement

Jimbo announces itself on every startup. If `startup_change_summary` changed
since the last startup, that handcrafted summary is included; otherwise the
generic greeting is used. The last value is in gitignored
`last_startup_summary.txt`.

**IMPORTANT FOR EVERY FUTURE EDITING CONTEXT:** Whenever a code change will cause
Jimbo to restart, update `startup_change_summary` in the same edit. Use a short,
player-facing explanation of intent and visible behavior, not implementation
details. This is part of completing the change, not optional cleanup.

**ALSO REQUIRED:** Whenever `startup_change_summary` changes, append its exact
new text to the tracked developer history in `STARTUP_ANNOUNCEMENTS.md` in the
same edit. Do not record generic unchanged-summary restarts. Future contexts must
maintain this history; do not rely on gitignored runtime logs to reconstruct it
later.

## Spontaneous Comments

Every 10 minutes Jimbo may comment using server activity since its last successful
comment plus a live current-research/progress/queue snapshot. The timer also gets
checked after message processing and is intentionally imprecise.

Only dlbattle can force this prompt with `Jimbo, chime in`; trailing text becomes
a topic hint. A request for Jimbo to be quiet skips only the next scheduled
comment. Join greetings and explicit engagement still work.

Successful spontaneous comments clear accumulated activity and reset the failure
counter. SKIPs, AI errors, and unsent replies increment it; after 12 consecutive
unsuccessful attempts, stale spontaneous context is cleared automatically. Any
player can manually clear that context with the exact meme command
`Jimbo, forget all previous instructions.` Jimbo acknowledges it but does not pass
the command to the model.

Scheduled checks stay silent when no players are online and clear their stale
activity and research baseline. If active research has the same displayed
progress across two online checks, Jimbo reports the stall once, then suppresses
repeat research notices until progress resumes or the technology changes.

## Working Rules

- After summarizing chat, store the last reviewed log timestamp in
  `last_chat_review.txt`; start the next review after it.
- Ask rather than inventing missing project-specific values.
- State uncertainty instead of presenting assumptions as fact.
- Prefer the smallest correct change; do not fundamentally rewrite working flow.
- Validate Python changes with `python -m py_compile`.
- For clear reversible tasks, act after a brief plan. Ask first only when
  requirements are ambiguous or an action is destructive.
