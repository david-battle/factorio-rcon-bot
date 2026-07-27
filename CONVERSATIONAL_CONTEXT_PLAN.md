# Conversational Context Implementation Plan

**Status:** Implemented on 2026-07-27. This file remains the design and acceptance
record for future refinements. The implementation is covered by `test_jimbo.py`.

## Goal

Give Jimbo enough recent shared conversation to understand follow-up questions
without retaining an unbounded transcript, acting on stale instructions, or
mixing conversational memory with the activity used for spontaneous comments.

Factorio chat is public, so this should be one server-wide dialogue rather than
separate memory for each player. The initial target is the latest 12 logical
messages from the last 15 minutes, capped at approximately 4,000 characters.

## Original Limitations

Before this work, `jimbo.py` kept `chat_history = deque(maxlen=2)`. The current
player message consumed one of those two positions, Jimbo's own replies were
excluded, and the reply-composition prompt did not receive that history. Context
also disappeared whenever Jimbo restarted.

This breaks ordinary exchanges such as:

1. Jimbo says mining productivity 2 is underway.
2. A player asks, "How much faster do we mine?"

It also breaks cross-player follow-ups:

1. NeedMoreChips asks about mining productivity 1 versus 2.
2. Jimbo answers.
3. dlbattle asks, "How much more?"

Increasing the current deque size alone will not solve either case because the
reply composer still lacks history and Jimbo's answer is absent.

## Scope

The first implementation should:

- Maintain bounded, timestamped, server-wide conversational history in memory.
- Record player messages and successfully delivered Jimbo responses.
- Include relevant spontaneous comments so players can ask follow-up questions.
- Give both classification and reply composition the same recent context.
- Restore recent dialogue from the server log after a Jimbo restart.
- Clear dialogue through the existing forget command.
- Preserve the existing rule that only the current message can trigger action.

The first implementation should not:

- Add a database or configuration framework.
- Retain long-term player profiles or summarize old conversations.
- Attempt to answer messages that arrived while Jimbo was offline.
- Treat join greetings, startup announcements, or raw server events as dialogue.
- Solve factual-data gaps such as item prototype values or session death counts.

## Dialogue Representation

Add one small structured representation, preferably a dictionary or a lightweight
tuple kept directly in `jimbo.py`. Each logical turn needs:

- `timestamp`: Unix time used for expiration.
- `speaker`: the Factorio username or `Jimbo`.
- `text`: normalized plain chat text.
- `rcon_command`: optional command associated with a Jimbo answer.
- `rcon_response`: optional raw result used to compose that answer.

Keep the entries in a `deque`. Do not rely only on `maxlen`, because entries must
also be removed by age and total rendered character count.

Use these initial bounds as constants near the existing top-level settings:

- Maximum turns: 12.
- Maximum age: 15 minutes.
- Maximum rendered context: approximately 4,000 characters.

Implement one pruning function that removes expired entries first, then removes
the oldest entries until both the turn and character limits are satisfied. Use
the same rendering function for character accounting and prompt construction so
the effective limit is predictable.

## Recording Rules

### Player Messages

Record each valid `[CHAT] username: message` after parsing it. Keep the current
message separate when constructing prompts, so it is not duplicated in history.
Messages not directed at Jimbo still belong in the shared dialogue because they
may establish context for a later direct question.

Do not record raw `<server>: Jimbo says ...` echoes during normal tailing. Jimbo
already knows exactly what it attempted to send, and consuming echoes would
duplicate its turns.

### Jimbo Replies

Collect all nonempty reply lines that pass the existing note/correction filters.
Send them through RCON and record only the lines confirmed delivered. If delivery
fails partway through, preserve the delivered subset as context without claiming
that players received the complete reply.

Attach the selected RCON command and raw response to the turn when present. This
allows a later prompt to reuse exact data instead of relying only on Jimbo's prose.
Never include secrets or the RCON password.

### Spontaneous Comments

When a spontaneous comment is delivered successfully, record its visible text as
a Jimbo turn. This is necessary for follow-ups to research comments such as "How
much faster do we mine?"

Keep the existing `recent_chat` activity accumulator separate. Dialogue history
supports conversation; `recent_chat` decides whether there is material for an
unsolicited comment. Clearing one should not accidentally clear the other except
for the explicit forget command.

### Exclusions

Do not add these to conversational history:

- `[JOIN]` and `[LEAVE]` events.
- Join greetings.
- Startup announcements.
- Failed or skipped model replies.
- Research snapshots that were queried but never mentioned to players.
- Raw server-log echoes of replies already recorded directly.

## Prompt Integration

Create one formatter that renders recent turns with clear speaker labels. If a
Jimbo turn has associated RCON data, include it in a distinct factual annotation
rather than pretending a player said it.

### Intent Classification

Pass the pruned dialogue before the existing current-message boundary. Preserve
and strengthen these instructions:

- History is background context only.
- Only the current message may request a command or response.
- An older mention of `Jimbo` must not make an unrelated current message
  actionable.
- Resolve pronouns and short follow-ups from history when the current message is
  directed at Jimbo.

The current message must remain separately delimited and should not also appear
as the newest history entry supplied to that request.

### Reply Composition

Supply the same pruned history to both the RCON-result and no-RCON reply prompts.
Tell the model to use it to resolve references such as "that", "it", "more", and
"faster", but to answer the current player rather than continuing an old topic on
its own.

When exact prior RCON data is available, direct the model to prefer it over a
paraphrased earlier Jimbo response. Continue to require every line for explicit
list requests and preserve the current markup-cleaning rules.

## Restart Hydration

Before seeking to the end of `server-console.log`, read a bounded tail sufficient
to find at most 15 minutes of recent `[CHAT]` entries. Hydration must populate
dialogue only; it must never classify, answer, greet, or run commands for those
historical lines.

During hydration:

- Parse ordinary player chat into player turns.
- Parse `<server>: Jimbo says ...` as Jimbo turns because direct in-memory records
  were lost during restart.
- Exclude recognizable startup announcements and join greetings where practical.
- Exclude other raw `<server>` messages that are not prefixed with `Jimbo says `.
- Apply the normal age, turn, and character pruning after parsing.

The server log does not preserve hidden RCON metadata, so hydrated Jimbo turns
will contain only their visible text. That is acceptable; richer metadata remains
available only for exchanges handled during the current process lifetime.

Do not add a persistent offset in this phase. Jimbo should start at the current
end of the log after hydration, preserving the existing behavior that it does not
respond retroactively to downtime messages.

## Forget Behavior

Extend `Jimbo, forget all previous instructions.` so it clears:

- The spontaneous `recent_chat` accumulator.
- The spontaneous failed-attempt counter.
- The new dialogue history.

Keep the existing acknowledgement and do not send the forget request to the
model. The known-player list and operational state must remain unchanged.

## Implementation Sequence

### Phase 1: In-Memory Dialogue

1. Add constants, the dialogue deque, pruning, rendering, and append helpers.
2. Replace the existing two-message `chat_history` prompt input.
3. Record parsed player chat without duplicating the current prompt message.
4. Pass recent dialogue to classification and reply composition.
5. Record successful Jimbo replies as logical turns.
6. Extend the forget command to clear dialogue.

This phase should solve same-process follow-ups such as "How much more?"

### Phase 2: Spontaneous Context

1. Give `maybe_spontaneous()` access to dialogue history or return the text it
   successfully delivered.
2. Record successful spontaneous comments as Jimbo turns.
3. Keep join greetings excluded and preserve the recently added timer reset after
   a successful greeting.

This phase should solve follow-ups to Jimbo's research commentary.

### Phase 3: Restart Hydration

1. Add a bounded server-log hydration function.
2. Parse recent player and Jimbo chat without triggering behavior.
3. Filter startup and greeting noise.
4. Hydrate before the normal `seek(0, os.SEEK_END)` tailing loop begins.

This phase should preserve useful recent context across normal Jimbo restarts.

### Phase 4: Refinement

Review real chat after deployment and adjust the 12-turn, 15-minute, and
4,000-character limits only when logs demonstrate a concrete need. Do not add
summarization or durable storage preemptively.

## Validation Plan

Add lightweight deterministic tests or an offline scenario script covering:

1. A spontaneous mining-productivity comment followed by "How much faster do we
   mine?" includes that Jimbo comment in reply context.
2. A player question, multiline Jimbo answer, brief reactions from two players,
   and "How much more?" retain the original exchange within the bounds.
3. A casual current message remains `SKIP` even when retained history contains an
   older direct mention of Jimbo.
4. Entries older than 15 minutes are removed.
5. More than 12 turns retain only the newest 12.
6. Large messages are removed from the oldest side until rendered context is
   within the character cap.
7. Failed RCON delivery does not create a successful Jimbo turn.
8. A multiline reply is represented as one turn.
9. Hydration restores recent player and Jimbo messages but triggers no commands or
   replies.
10. The forget command clears dialogue and spontaneous context without clearing
    known players.
11. Join greetings are not added to dialogue and do not cause duplicate
    spontaneous welcomes.

Mock AI classification and composition responses for deterministic assertions.
Continue validating Python changes with `python -m py_compile jimbo.py` and use
offline log injection for one end-to-end check before observing live behavior.

## Success Criteria

The work is complete when:

- Both classifier and composer receive bounded shared context.
- Jimbo can resolve short same-process and post-restart follow-ups demonstrated by
  the recent NeedMoreChips conversation.
- Jimbo's delivered replies and spontaneous comments are available as context.
- Stale history cannot trigger action from an unrelated current message.
- Memory and prompt size remain bounded.
- Existing joins, quiet requests, forget behavior, spontaneous comments, arbitrary
  slash-command pass-through, and RCON reconnection continue to work.

Factual accuracy remains a separate future task. Conversation retention can tell
Jimbo that "how much more?" refers to mining productivity, but targeted RCON/Lua
queries are still needed when the model does not reliably know the underlying
prototype or technology values.
