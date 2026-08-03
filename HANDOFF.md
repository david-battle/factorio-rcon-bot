# Handoff

## Verified State

- Branch: `main`; local commits only (the user pushes manually).
- **Jimbo is running** under pid `346199` (see `jimbo.pid`), started 2026-08-03
  05:51 per `docs/OPERATIONS.md`, verified alive. Single instance only.
- **Jimbo is muted by the OpenRouter free-tier rate limit as of ~07:14**
  (`429 free-models-per-day`, 50/day, `X-RateLimit-Remaining: 0`). All AI calls
  — greetings and replies — fail with `Temporary AI error; retrying`. Reset at
  midnight UTC (per user). No code fix; either wait for reset or top up
  credits.
- `last_startup_summary.txt` matches the current `startup_change_summary` ("I was
  occasionally failing to answer..."), so the current running process already
  announced the latest change and no further `STARTUP_ANNOUNCEMENTS.md` entry is
  needed for another restart of this same code.
- This session's code changes are committed in `be69ab3` (jimbo.py,
  test_jimbo.py, STARTUP_ANNOUNCEMENTS.md, docs/OPERATIONS.md).

## Completed Work

Fixed Jimbo's recurring "I couldn't complete that request" failures, diagnosed
from `jimbo.log` (three occurrences 2026-08-03 05:22–05:29):

- **Truncation root cause.** Nemotron 3 Ultra is a reasoning model; it spends
  ~150–260 tokens on internal "thinking" before answering. The profile's
  `max_completion_tokens: 256` left almost no budget for the visible reply, so
  replies got cut mid-sentence ("Threevee dropping blue science at"). Bumped to
  1024 in the `nemotron` profile.
- **Reasoning leaking into classifier output.** The strict one-line chat
  classifier sometimes returned its chain-of-thought as content (e.g. "The user
  is asking for... The appropriate command is TAG...") instead of
  `PRODUCE|...` / `TAG|...`, so it was treated as an unrecognized response.
  Added `extra_body: {"reasoning": {"exclude": True}}` to the `nemotron`
  profile; verified it returns only the final answer.
- **Classifier hardening.** Added `_is_recognized_classification()` and a
  one-shot retry in `classify_current_message()` that nudges the model once when
  its output is unrecognized prose, empty, or malformed (mirrors the existing
  SKIP-retry). Also makes the step-3 reply path non-empty more often.
- Updated `startup_change_summary` to a player-facing "replies complete more
  reliably" line and appended a `## 2026-08-03` entry to
  `STARTUP_ANNOUNCEMENTS.md` (both restart-summary and announcement entry for
  this change; the earlier truncation-fix entry from this same date is retained).
- Recorded the Nemotron reasoning behavior in `docs/OPERATIONS.md` (AI Provider
  section) so future providers keep a generous completion cap and reason
  exclusion.

## Validation

- `python -m py_compile jimbo.py` clean; `git diff --check` clean.
- `python -m unittest test_jimbo` — 121 tests, all passing (2 added for the
  classifier retry, plus an assertion for the `reasoning.exclude` config).
- Live: restart at 05:51 announced the change; a multi-sentence direct reply
  completed without truncation. Empirically reproduced the classifier leak and
  confirmed `reasoning: {exclude: true}` cleans it up (documented in
  OPERATIONS.md).
- Not run: `test_ollama.py` (per operations guidance, avoid while the Factorio
  client uses the GPU).

## Remaining Work

- None pending. The `reasoning: {exclude: true}` path is live for the current
  save; watch a few more direct/classifier requests to confirm the fallback
  rate drops. The overnight crash cause from the prior handoff remains
  unconfirmed; no startup supervisor unless the user asks.
- Residual limitation: `TAG` cannot filter assembling machines by their current
  recipe ("Jimbo ping the assembling machine making X"). `exclude` + the retry
  improve but do not fully solve that ambiguous case. See
  `docs/FUTURE_DIRECTIONS.md` for broader intent work.

## Current Model

- Jimbo runs on `nemotron` (`nvidia/nemotron-3-ultra-550b-a55b:free` via
  OpenRouter, `openrouter.key`), `max_completion_tokens: 1024`, with
  `reasoning: {exclude: True}`. Changed this session.

## Operational Caveats

- Ensure only one Jimbo instance. If restarting, kill the old process first
  (see `docs/OPERATIONS.md`). The launcher via `setsid` forks, so confirm the
  recorded PID with `ps` from a fresh session (the `$!` name is the wrapper).
- Only stage intentional changes. `*.key`, `rconpw`, `groq-api-key.txt`,
  `jimbo.log`, `jimbo.pid`, `jimbo_says.log`, `last_*.txt`, and
  `known_players.txt` remain ignored/untracked.
- The old repository (`/mnt/d/ChatGPT-Factorio-Playground/factorio-blueprints`)
  used the deprecated `mcrcon` library; do not import its RCON code.
- 2026-08-01 learnings apply: chat delivery uses
  `/silent-command game.forces.player.print(...)` with
  `sound_path="item-move/logistic-robot"` and `ensure_ascii=False` (Factorio's
  Lua 5.1 rejects `\uXXXX` escapes). See `docs/RCON_NOTES.md`.

## Natural Next Action

- Watch for the rate-limit reset (midnight UTC) and confirm Jimbo resumes
  replying; if the 429 persists, the OpenRouter account needs a credit top-up.
  Otherwise wait for the user's next request. If the "I couldn't complete"
  fallback still appears for hard requests, consider classifier-prompt work for
  recipe-filtering requests (see `docs/FUTURE_DIRECTIONS.md`).