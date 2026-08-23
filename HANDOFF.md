# Handoff

## Verified State

- Branch `main`; local commits only (the user pushes manually).
- **Jimbo is RUNNING** (PID from `jimbo.pid`, `python -u jimbo.py`, gitignored
  `jimbo.log`). This differs from the previous handoff, which left it down
  intentionally; this session restarted it repeatedly for live tests. Leave it
  running unless the user says otherwise.
- `ai_profile_name = "deepseek"` (jimbo.py, top config block) — the paid
  `deepseek-v4-flash` via OpenCode Zen (`https://opencode.ai/zen/v1`, reading
  the `opencode` credential from `~/.local/share/opencode/auth.json`; never
  read or print a token). The `server_owner` / `ai_profiles` values stayed in
  that single block per the always-preserve rule.
- Factorio is up: RCON answers on `127.0.0.1:27015`, `/version` reports
  `2.1.14`. Server log at `/mnt/d/factorio-server/server-console.log`.
- The backup loop state is unchanged from commit `ba1c957`; not touched this
  session.

## Completed Work

### AI provider switch (paid DeepSeek, latency)

- `jimbo.py:67` now selects `deepseek` (`deepseek-v4-flash`) after the owner
  added OpenCode credit; no more free-quota truncation.
- `warm_up_ai()` fires one throwaway `"Reply with exactly: ok"` call right
  after the online announcement to absorb a measured one-time cold-start
  penalty (~7–19 s) while nobody waits. `ask_ai` logs each call duration.
- `docs/OPERATIONS.md`: updated the profile table, added a "Model Call Latency
  Findings" section (first-call penalty; completion-token caps hurt because
  reasoning tokens count against them; client reuse does not help), and updated
  the Provider History. Also added upgrade step 9 (regenerate the Lua
  reference).

### First-command-swallow fix

- Factorio holds the first Lua console command of a fresh map session behind
  the achievements warning and drops it silently. `prime_lua_console()` sends a
  doubled no-op `/silent-command local x=1` at startup
  (`lua_console_prime_command`). Documented in `docs/RCON_NOTES.md`.

### Two-layer Lua/RCON fluency (directions 10 & 11 in FUTURE_DIRECTIONS.md)

- **Layer 1 — essentials block.** `generate_lua_reference.py` parses the
  installed game's `doc-html/runtime-api.json` into `lua_essentials.txt`
  (~6 KB: global objects, global functions, full class index, core
  abort-rules). Both files committed; the source JSON is never committed.
  Injected into classification prompts only (not replies), to protect latency.
- **Layer 2 — on-demand LOOKUP.** New structured decision
  `LOOKUP|class-a,class-b|question`: `parse_lookup_decision`,
  `load_runtime_api_doc`, `_collapse`, `_format_type`, `extract_api_slices`
  (budget-capped, ~14 KB, `[truncated]` marker), `FORBIDDEN_LUA_CHECKS`,
  `forbidden_lua_reason` (grants, teleports, destroys, non-ghost entity
  spawns, file writes; `table.insert` and ghost `create_entity` pass),
  `strip_code_fences`, `build_lookup_prompt`, `compose_lookup_command`, and
  the `RCON: scripted lookup` dispatch with its verified-reporting reply hint.
- `docs/BOT_CONTRACTS.md`: added a ghost/blueprint-placement carve-out (never
  declined as cheating) and a "Scripted Lookup" section. `FUTURE_DIRECTIONS`
  direction 11 Status notes Layers 1 and 2 shipped 2026-08-23.

### Honest-counting hardening (fixes the `90498` overestimate)

- `build_lookup_prompt` now requires the composed command to print a scope
  line (what it scanned) and which inventories it EXCLUDES when one line can't
  cover belts/trains/cars/player.
- `lookup_hint` forbids "exactly"/"all" unless the response itself states full
  coverage, and forbids reusing stale numbers from earlier conversation.
- `logistics_hint` rewritten: report ONLY counts literally in the response;
  never reuse a number from earlier; when the query reports no logistic
  networks, say so plainly instead of inventing a quantity.
- Classifier routing split: `LOGISTICS` is network-stock only; physical
  container/belt/inventory item counts (e.g. "how many iron plates exist on
  Nauvis") now route to `LOOKUP`, with a `...stored in chests on nauvis`
  example added.

### Audit trail

- Every LOOKUP now appends timestamp + question + composed command + raw
  response to the gitignored `jimbo_commands.log`; the command also prints to
  `jimbo.log`. `.gitignore` updated.

## Validation

- `python -m py_compile jimbo.py test_jimbo.py generate_lua_reference.py` OK.
- `python -m unittest test_jimbo` — 146 passed.
- `git diff --check` clean.
- Did NOT run `test_ollama.py` (the Factorio client is using the GPU).

## Remaining Work

- The original `90498` iron-plate figure was never traced to its exact command:
  `/silent-command` is not written to `server-console.log`, and `jimbo.log`
  was truncated at restart before the command was logged. Treat any pre-audit
  stated number as unverified.
- Re-ask "how many iron plates exist on Nauvis?" to confirm the routing split
  now sends it to a container-scanning LOOKUP that prints a scope line; check
  `jimbo_commands.log` to audit the composed command. Not done live yet after
  the routing change.
- If counting items across every container/belt/inventory proves too heavy or
  slow for one line, the scope line keeps replies honest; worth a
  `FUTURE_DIRECTIONS` note only if it becomes a problem.

## Operational Caveats

- Only stage intentional changes. `*.key`, `rconpw`, `jimbo.log`, `jimbo.pid`,
  `jimbo_says.log`, `jimbo_commands.log`, `backup_loop.*`, `last_*.txt`,
  `known_players.txt`, `restart_server.py`, `new_game.py` remain
  ignored/untracked (machine-local operator data).
- Do not restart or stop Jimbo/Factorio as part of a handoff unless the user
  asks; leave the current running process alone.

## Natural Next Action

- Live-test the container-count routing with the "iron plates on Nauvis"
  probe, read the composed command from `jimbo_commands.log`, then push the
  handoff commit (user pushes manually).
