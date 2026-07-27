# Jimbo - Factorio RCON Bot

## Scope

This is a deliberately simple Factorio bot in `~/factorio-rcon-bot` on branch
`main`. It reads server activity, asks an AI model what to do, and uses RCON for
queries and chat replies. Do not add unrequested features or infrastructure such
as databases, web servers, or configuration frameworks.

## Conditional Reference

Read `OPERATIONS.md` when a task involves environment setup, RCON connectivity,
AI provider/model changes, local Ollama fallback, process management, live or
offline testing, `known_players.txt` seeding, or runtime-pitfall diagnosis.

**If this coding context is running on a local model through Ollama, read
`OPERATIONS.md` before editing anything.** It contains the local model's memory,
latency, and coding-workaround constraints plus provider-switch history.

For weaker local Ollama coding models: if Edit cannot repair Python whitespace,
replace the complete enclosing function or file with Write, then validate with
`python -m py_compile`.

## Environment Essentials

- Bot: WSL native filesystem at `~/factorio-rcon-bot`.
- Server: Windows native at `D:\factorio-server`.
- Input log: `/mnt/d/factorio-server/server-console.log`.
- RCON: `rcon.source.Client` at `127.0.0.1:27015`.
- Password: gitignored `rconpw`; never hardcode, print, or commit it.
- Python dependencies: shared `/mnt/d/.venv` activated by `.bashrc`.

Do not substitute another RCON library; this exact connection is verified.

## Architecture

Keep three conceptual moving parts:

1. Server log input.
2. AI decisions and reply composition.
3. RCON queries/actions and chat output.

## Chat Listener

- Chat format: `YYYY-MM-DD HH:MM:SS [CHAT] username: message text`.
- Join/leave events use `[JOIN]` and `[LEAVE]`.
- Split on `[CHAT] ` before `: ` because timestamps contain colons.
- Ignore messages beginning with `Jimbo says ` to avoid processing bot echoes.
- `[JOIN]` triggers a model-generated greeting. `known_players.txt` determines
  whether the model is told that the player is new or returning.
- Windows writes can invalidate WSL log handles. Catch both `OSError` and
  `ValueError`, then reopen the log.

## Request Flow

1. Parse a new chat line into username and message.
2. Ask the model for SKIP, NONE, PLATFORMS, PLANETS, or a slash command.
3. Run canned platform/planet Lua or the selected built-in command if needed.
4. Ask the model to compose a short reply from the player message and RCON data.
5. Send each reply line separately as raw RCON text prefixed with `Jimbo says `.

The classifier defaults to SKIP unless the current message contains "Jimbo" so
the bot does not interrupt player-to-player chat. No-RCON replies may also SKIP.
Strip output lines beginning with `(Note:` or `(Corrected`.

### Intentional Flexibility

The classifier may return any slash command, and the bot intentionally passes it
through to RCON. Do not add a command whitelist unless explicitly requested.
Occasional joking claims that an action is underway without RCON execution are
part of Jimbo's humor and do not need guardrails.

## RCON Commands

- `/players`: all players who have played this save.
- `/players online`: currently connected players.
- `/evolution`: enemy evolution factor.
- `/time`: elapsed server/game time, not wall-clock time.
- `/version`: Factorio version. Do not use nonexistent Lua properties
  `game.product_version` or `game.build_version`.
- Plain Lua often returns nothing; use `rcon.print()` inside `/silent-command`.
- Raw RCON text without a slash appears in chat as `<server>`.

Canned platform query:

```text
/silent-command local list={};for _,surface in pairs(game.surfaces) do if surface.platform then table.insert(list,surface.platform.name) end end;rcon.print(table.concat(list,"\n"))
```

Canned planet query:

```text
/silent-command local list={};for _,surface in pairs(game.surfaces) do if surface.planet then table.insert(list, surface.planet.name:sub(1,1):upper()..surface.planet.name:sub(2)) end end;rcon.print(table.concat(list,"\n"))
```

When replying with platform names, strip Factorio markup brackets but preserve
their contents and surrounding text. Include every result when a list is asked
for. Multi-line replies require one RCON command per line.

## AI Provider

The current model is `openai/gpt-5.4-mini`, invoked by `ask_ai()` through
`opencode run --pure --agent jimbo --format json`. The injected agent has no tools
or filesystem access. It runs from `/tmp/opencode` with project configuration and
external skills disabled, so in-game Jimbo does not receive this file.

Reply prompts derive self-identification from `model_name` in `jimbo.py`; update
that one value when switching models. Prompts identify dlbattle as server owner.
For provider setup, quota history, and local fallback, read `OPERATIONS.md`.

## Startup Announcement

Jimbo announces itself on every startup. If `startup_change_summary` changed
since the last startup, that handcrafted summary is included; otherwise the
generic greeting is used. The last value is in gitignored
`last_startup_summary.txt`.

**IMPORTANT FOR EVERY FUTURE EDITING CONTEXT:** Whenever a code change will cause
Jimbo to restart, update `startup_change_summary` in the same edit. Use a short,
player-facing explanation of intent and visible behavior, not implementation
details. This is part of completing the change, not optional cleanup.

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

## Current TODOs

- Add retry/backoff for transient AI errors, especially HTTP 429.

## Working Rules

- Ask rather than inventing missing project-specific values.
- State uncertainty instead of presenting assumptions as fact.
- Prefer the smallest correct change; do not fundamentally rewrite working flow.
- Use `print(..., flush=True)` in long-running redirected Python processes.
- Validate Python changes with `python -m py_compile`.
- For clear reversible tasks, act after a brief plan. Ask first only when
  requirements are ambiguous or an action is destructive.
