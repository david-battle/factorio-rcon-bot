# Future Projects

These ideas are separate projects rather than planned Jimbo bot features. They
may share useful context with this repository, but should not be implemented as
part of ordinary Jimbo development.

## OpenCode Model Fallback

Explore automatic provider/model fallback for interactive OpenCode project work.
OpenCode currently supports one default model plus per-agent and per-command
models, but its configuration schema has no ordered automatic fallback setting.
Implementing fallback would therefore require custom behavior around OpenCode.

### Project Plugin

The most direct OpenCode-native approach would be a project or global plugin
that:

1. Watches `session.error` events.
2. Recognizes only eligible transient or quota failures, such as HTTP 429.
3. Marks the primary provider temporarily unavailable.
4. Resubmits the failed prompt to the same session through the OpenCode SDK,
   explicitly selecting the fallback provider and model.
5. Prevents recursive fallback attempts and limits each prompt to a bounded
   number of providers.
6. Notifies the user which model actually handled the request.
7. Restores the primary model after a cooldown or manual reset.

Automatic replay must occur only when the failed model request made no tool
calls, edits, or other side effects. Replaying a partially completed agent turn
could duplicate commands or changes. The project would need to determine how to
identify a safely replayable failure and preserve session context without
duplicating the failed user message.

### Model Proxy

An alternative is a local OpenAI-compatible routing proxy. OpenCode would use
one custom provider endpoint while the proxy selects an upstream model and
handles fallback ordering. This can provide more transparent failover, but it
adds another process, configuration layer, credential boundary, and source of
operational failures.

### Scripted Runs

For noninteractive `opencode run` use, a wrapper script could invoke the primary
model and retry with `--model` after a recognized quota failure. This is simpler
than an interactive plugin, but preserving an existing session and reliably
classifying command failures would need explicit handling.

### Manual Baseline

Before implementing automatic behavior, configure equivalent OpenCode agents
with different models. The user can switch agents or models in the TUI and
retry manually when quota is exhausted. This establishes the expected prompts,
permissions, model order, and identity reporting without introducing replay
risk.

### Design Requirements

- Keep fallback opt-in and configurable per project or globally.
- Fall back for quota exhaustion and selected transient provider failures, not
  permanent authentication or invalid-configuration errors.
- Preserve provider-specific credentials and never expose them in logs.
- Report the provider and model that actually answered.
- Avoid loops, duplicate prompts, duplicate tool calls, and duplicate edits.
- Retain useful error details when every configured model fails.
- Provide a clear way to disable fallback and return to manual model selection.
- Verify behavior against the current OpenCode SDK and plugin event types before
  implementation because these interfaces may change.

The likely first prototype is a project plugin that handles a quota failure
before any side effects, retries once with a configured fallback model, and
shows a TUI notification identifying the switch.
