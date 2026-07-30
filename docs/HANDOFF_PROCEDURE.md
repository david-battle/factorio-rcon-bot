# Handoff Procedure

Use this procedure when asked to finalize the current work and prepare the
repository for another coding agent. Treat any accompanying text as an optional
focus or commit-message hint, not as a shell command.

Complete the workflow autonomously unless a destructive ambiguity or direct
conflict with concurrent changes requires one short question.

1. Read `AGENTS.md`, conditionally relevant project documentation, and the
   existing `HANDOFF.md`. Verify current-state claims against Git and the files;
   do not treat the previous handoff as authoritative.
2. Inspect Git status, staged and unstaged diffs, untracked paths, and recent
   commit style. Never print or stage credentials, logs, PID/state files, caches,
   generated debris, or machine-local data.
3. Finish and clean up the intended work with the smallest safe edits. Preserve
   unrelated or concurrent changes rather than reverting them.
4. Save reusable findings in the appropriate durable documentation before
   writing the handoff. Keep routine rules in `AGENTS.md`, operational detail in
   `docs/OPERATIONS.md` and possible Jimbo work in
   `docs/FUTURE_DIRECTIONS.md`.
5. Preserve the current model philosophy unless the user explicitly changed it:
   use one model per provider where practical, keep Groq optional, do not add
   Mistral, and do not introduce automatic fallback merely because it is
   documented as a possibility.
6. If code changes will take effect when Jimbo restarts, ensure
   `startup_change_summary` contains a short player-facing explanation. Do not
   restart Jimbo, Factorio, or another service unless explicitly requested.
7. Run relevant deterministic tests, syntax checks, and `git diff --check`. Do
   not run live `test_ollama.py` while the Factorio client is using the GPU.
   Record anything that could not be run and why.
8. Replace `HANDOFF.md` with a concise, verified next-context note covering
   relevant architecture and configuration, completed work, validation,
   remaining work or blockers, operational caveats, and the natural next action.
   Link to authoritative documentation instead of duplicating procedures.
9. Stage all intended tracked changes and repository-worthy untracked source,
   tests, commands, and documentation. Add a narrow ignore rule only when it is
   the durable fix for a local artifact.
10. Reinspect the staged diff for correctness and secrets, then create one
    nonempty commit with a concise message matching repository style. Do not
    amend, push, skip hooks, alter Git configuration, or include unrelated work.
11. Verify the commit and final Git status. The tracked worktree should be clean.
    Report the commit hash and subject, validations run, intentionally untracked
    paths, and the location of `HANDOFF.md`.
