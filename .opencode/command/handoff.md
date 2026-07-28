---
description: Finalize repository changes, commit them, and prepare the next context.
agent: build
---

Finish the current development context and leave this repository ready for the
next one. Treat any text after `/handoff` as an optional focus or commit-message
hint, not as a shell command: `$ARGUMENTS`

Complete the workflow autonomously unless a destructive ambiguity or a direct
conflict with concurrent changes requires one short question.

1. Read `AGENTS.md` and any conditionally relevant project documentation. Read
   the existing `HANDOFF.md` if present, but verify every claim against the
   current repository instead of treating it as authoritative.
2. Inspect `git status`, all staged and unstaged diffs, and recent commit style.
   Review every modified tracked file and every untracked path. Never print or
   stage credentials, runtime logs, PID files, caches, generated debris, or
   machine-local state.
3. Clean up the intended repository changes with the smallest safe edits. Keep
   Jimbo deliberately simple; do not add features or infrastructure merely to
   make the handoff look complete. Preserve unrelated or concurrent work rather
   than reverting it.
4. Keep durable documentation in the right place:
   - Save any recent reusable learnings from the current context in the
     appropriate Markdown file before writing `HANDOFF.md`.
   - `AGENTS.md` contains only rules future coding contexts routinely need.
   - `OPERATIONS.md` contains setup, provider history, recovery, process, and
     other infrequently needed operational detail.
   - `FUTURE_DIRECTIONS.md` contains possible future Jimbo work.
   - `FUTURE_PROJECTS.md` contains ideas that are separate projects.
5. Preserve current model philosophy unless the user explicitly changed it:
   keep one model per underlying provider where practical; do not add Mistral;
   keep Groq optional; and do not implement automatic fallback merely because
   it is documented as a future possibility.
6. If code changes will take effect when Jimbo restarts, ensure
   `startup_change_summary` has a short player-facing explanation. Do not
   restart Jimbo, Factorio, or another service unless explicitly requested.
7. Run the relevant deterministic tests, syntax checks, and `git diff --check`.
   Do not run the live `test_ollama.py` smoke script while the Factorio game
   client is using the GPU. Record any test that cannot be run and why.
8. Create or replace `HANDOFF.md` with a concise, verified next-context note.
   Include the current architecture/configuration that matters, work completed,
   validation performed, remaining work or known blockers, operational caveats,
   and the natural next action. Exclude secrets, volatile PIDs, raw chat, and
   details already maintained authoritatively elsewhere; link to the relevant
   file instead of duplicating long procedures.
9. Stage every modified tracked file after review. Stage untracked source,
   tests, commands, and documentation that belong in the repository. For local
   artifacts that should remain untracked, add a narrow ignore rule when that is
   the durable fix; otherwise leave them untouched and report them.
10. Reinspect the staged diff for correctness and secrets, then create one
    non-empty commit with a concise message matching repository style. Do not
    amend, push, skip hooks, alter Git configuration, or include unrelated
    external repositories. If validation or a hook fails, fix the issue and
    create a normal commit only after it passes.
11. Verify the resulting commit and `git status`. The tracked worktree should be
    clean. Report the commit hash and subject, validations run, any intentionally
    untracked paths, and the location of `HANDOFF.md`.
