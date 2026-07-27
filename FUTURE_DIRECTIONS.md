# Future Directions

Jimbo should become more aware of what is happening across the server without
turning into a noisy monitoring system or requiring players to memorize exact
commands. These are ideas to explore, not committed implementation plans. Any
work should preserve the bot's simple architecture and favor useful context,
natural interaction, and restrained behavior.

1. **Refine shared conversational context.** The first bounded server-wide
   dialogue is implemented: 12 turns, 15 minutes, about 4,000 characters, Jimbo's
   delivered replies, relevant RCON facts, and restart hydration. Future work
   should tune those limits only from observed chat and consider richer context
   only when a concrete failure remains. See `CONVERSATIONAL_CONTEXT_PLAN.md` for
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

4. **Formal offline scenario harness.** The project already supports manual log
   injection and mocked AI or RCON checks. Formalize that capability into a small,
   deterministic scenario harness for complete flows such as chat classification,
   follow-up replies, joins, spontaneous comments, failures, and fuzzy trigger
   matching. It should remain lightweight and should not introduce a testing or
   configuration framework larger than the bot itself.

Context and factual knowledge are separate problems. A larger dialogue window
would not have prevented the incorrect solid-fuel energy answer, and the current
server log does not expose enough information to answer session death counts.
Prototype values, technology effects, and similar factual questions should
eventually use targeted RCON/Lua queries. Death tracking would require explicit
game instrumentation or another reliable event source rather than model memory.

The strongest product direction is a combination of event-aware context and
natural situational awareness. A useful first exploration would identify the
small set of server conditions Jimbo should understand continuously, beginning
with per-surface power health, then decide how players can ask about those
conditions conversationally and when Jimbo should mention them unprompted.
