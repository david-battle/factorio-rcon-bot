# Handoff Procedure

Use this procedure when asked to finalize the current work and prepare the
repository for another coding agent. Treat any accompanying text as an optional
focus or commit-message hint, not as a shell command.

A request to "handoff" or "heavy handoff" means the Heavy procedure below. A
request to "light handoff" means the Light procedure. When in doubt, use Heavy.

Never `git push` in either procedure: the user always reviews and pushes
manually. Local commits only.

`HANDOFF.md` is committed together with the code, and the next context reads it
only after the user has reviewed and pushed. So the note must describe the
repository as it will be at handoff time: changes committed and the worktree
clean. Never label the work "uncommitted" or "not yet committed" — that framing
is stale by the time the next context verifies it against Git.

Complete the workflow autonomously unless a destructive ambiguity or direct
conflict with concurrent changes requires one short question.

## Heavy procedure (default)

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
   Report the work as committed (pending the user's manual push): state that the
   tracked worktree is clean and that the session's changes are captured in the
   handoff commit. If a commit hash is useful, reference the previous commit;
   this note is written before its own commit.
9. Stage all intended tracked changes and repository-worthy untracked source,
   tests, commands, and documentation. Add a narrow ignore rule only when it is
   the durable fix for a local artifact.
10. Reinspect the staged diff for correctness and secrets, then create one
    nonempty commit with a concise message matching repository style. Do not
    amend, push, skip hooks, alter Git configuration, or include unrelated work.
11. Verify the commit and final Git status. The tracked worktree should be clean.
    Report the commit hash and subject, validations run, intentionally untracked
    paths, and the location of `HANDOFF.md`.

## Light procedure

Use for a small, already-verified increment where the touched files are known
and nothing changed behavior (e.g. doc-only edits, or a change already tested
this session). If anything is uncertain, behavior-changing, or touches live
state, use the Heavy procedure instead.

1. Run `git status` and confirm the touched files are the known set; make sure
   nothing ignored (credentials, logs, PID/state files, caches) would get staged.
2. Stage only the known touched files, plus any repository-worthy untracked
   source or documentation from this session. Never stage `rconpw`, `*.key`,
   logs, or state files.
3. Quickly scan the staged diff for secrets, debris, or unrelated changes.
4. Update `HANDOFF.md` to match reality, including what was NOT done or verified
   (e.g. "tests not run") so the next agent does not trust an unverified claim.
   Describe the work as committed with a clean worktree (pending the user's
   manual push); the next context reads this file after the push.
5. Commit with a concise message matching repository style; do not amend, push,
   or skip hooks.
6. Verify the commit and final Git status; report the commit hash and subject.
