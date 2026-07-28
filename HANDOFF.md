# Handoff

## Current State

- Branch: `main`; this work started from `origin/main` at `ceb14ad`.
- Jimbo is running as PID `169933` with the active
  `openai/gpt-5.4-mini` OpenCode profile. The predefined DeepSeek, Groq, and
  Ollama profiles remain manual alternatives with no automatic fallback.
- The latest reviewed server chat timestamp is `2026-07-28 17:06:19`.
- `startup_change_summary` describes the all-planet logistic availability path
  and has already been announced by the running process.

## Completed Work

- Corrected repeatable research naming to use `LuaTechnology.level` and natural
  player-facing names such as `mining productivity 8`.
- Added Factorio 2.0 recipe lookup guidance using `prototypes.recipe`.
- Added validated `LOGISTICS|surface|item-name,item-name` decisions. The canned
  read-only query supports one planet or `all`, separates networks, marks
  silo-connected networks, sums nonnegative quality-aware availability, and keeps
  stock distinct from recipe shortfall.
- Added deterministic failure acknowledgments for objective classifier, RCON,
  reply-composition, and delivery failures. Unrecognized classifier output is now
  logged verbatim; intentional SKIP decisions remain silent.
- Added 11 deterministic tests, increasing `test_jimbo.py` from 25 to 36 tests.
- Documented logistic availability, logistic-group mutation, quality constraints,
  rollback, and mutation verification in `AGENTS.md` and `OPERATIONS.md`.
- Documented local Codex, Antigravity, and checksum-verified GitHub CLI installs
  in `SYSTEM_ADMIN.md`. `gh` 2.96.0 is authenticated as `david-battle`; its token
  has unnecessarily broad scopes and should eventually be replaced.

## Live Server Work

- The development assistant, not the running Jimbo, created force-wide
  `with_trash` group `jimbo's nonos` from all 85 current
  `intermediate-products` item prototypes. It has two attached members.
- The assistant later changed spoilage to normal quality `min=200,max=200` and
  retained `0/0` for uncommon, rare, epic, and legendary spoilage. Independent
  verification found 89 total filters with the five spoilage filters correct.
- These were direct RCON actions announced with `Jimbo says ` and must not be
  represented as capabilities successfully exercised by the running Jimbo.

## Validation

- `python -m py_compile jimbo.py test_jimbo.py` passed.
- `python -m unittest -v test_jimbo` passed all 36 deterministic tests.
- `git diff --check` passed.
- Live checks verified repeatable research naming, single-planet and all-planet
  logistic results, group persistence, shared filter mutation, and rollback
  mechanics against Factorio 2.1.12.

## Remaining Work

- Primary next action: enforce the documented mutation-success rule in runtime
  code. A bare `/silent-command` currently produces an empty response and can
  still reach reply composition; Jimbo falsely claimed it had changed the
  spoilage group after exactly this no-op. Mutating requests must require a
  nonempty executable command and printed verified outcome, otherwise use the
  deterministic failure acknowledgment.
- If Jimbo should manage named logistic groups itself, add a structured mutation
  path using the transactional procedure in `OPERATIONS.md`, rather than relying
  on arbitrary model-generated Lua.
- Replace the GitHub CLI token with least-privilege scopes when convenient.

## Operational Caveats

- Do not restart Jimbo, Factorio, or another service merely to resume work.
- Do not replay mutating RCON commands after an uncertain disconnect.
- Credentials, runtime logs, PID/state files, player data, caches, local tools,
  and `last_chat_review.txt` remain ignored and must not be committed.
