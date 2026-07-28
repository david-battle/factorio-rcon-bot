# Conversational Context Record

**Status:** Implemented on 2026-07-27. `AGENTS.md` defines the current behavioral
rules, `jimbo.py` is authoritative for implementation, and `test_jimbo.py`
provides deterministic coverage.

## Purpose

Jimbo keeps enough recent public conversation to resolve ordinary follow-ups
without retaining an unbounded transcript, acting on stale instructions, or
mixing dialogue with activity accumulated for spontaneous comments. Context is
server-wide because Factorio chat is public.

The initial implementation replaced a two-message player-only history that was
not available to reply composition and disappeared on restart. It uses one
timestamped dialogue deque bounded to 12 logical turns, 15 minutes, and roughly
4,000 rendered characters.

## Invariants

- Record player messages, successfully delivered Jimbo replies, relevant
  spontaneous comments, and exact RCON facts associated with replies.
- Keep the current message outside rendered history. History may resolve a
  reference but only the current message may trigger a response or command.
- Record a multiline Jimbo reply as one logical turn and only after successful
  delivery; preserve a delivered subset if sending fails partway through.
- Exclude joins, leaves, greetings, startup announcements, failed replies, and
  duplicate server echoes during normal tailing.
- Keep dialogue separate from spontaneous activity. Direct replies clear
  addressed activity but remain in dialogue; the forget meme clears both.
- Prune by age, turn count, and rendered size through the same rendering path
  used for prompts.

## Restart Hydration

Startup reads a bounded tail of `server-console.log`, restores recent player and
`Jimbo says` chat, filters greeting and startup noise, and resumes tailing from
the hydration endpoint. Hydration never classifies historical messages, sends
replies, or runs commands. The log cannot restore hidden RCON metadata, so
hydrated Jimbo turns contain visible text only.

## Validation

Deterministic tests cover same-process and post-restart follow-ups, cross-player
context, all three bounds, stale-history isolation, multiline and partial
delivery, hydration without retroactive action, exclusion of greetings, and the
forget command. Future tuning should follow observed chat failures rather than
adding summarization, durable storage, or larger context preemptively.

Conversational memory does not solve factual-data gaps. Prototype values,
technology effects, death counts, and similar facts still require targeted
RCON/Lua queries or another reliable event source.
