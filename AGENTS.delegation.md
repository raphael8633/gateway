# AGENTS.delegation.md (gateway)
<!-- raph-power-managed-delegation: v1 -->

This file applies only when a Codex session is using a sub-agent / delegation workflow.
If no delegation is in use, stop here and return to `AGENTS.md`.

## Universal delegation rules

@/home/ubuntu/projects/raph-power/shared/delegation.md

The above defines the opt-in trigger, routing, progress logging, prompt
packaging, and review gates. Apply it as written.

## Codex-specific notes

**Delegation is opt-in.** Do not delegate based only on task classification.
The main Codex agent may execute S0–S3 tasks directly.

When delegation is explicitly requested by the user or applicable instructions:

- Use Codex native collaboration tools (`spawn_agent`, `send_message`,
  `followup_task`, `wait_agent`, and related runtime-provided tools).
- Delegate only concrete, bounded work that can proceed independently.
- Do not invoke Claude CLI or any other external model CLI as a sub-agent.
- Do not route models or providers by S1/S2/S3 classification.
- Keep implementation and review in the main agent unless the explicit
  delegation request covers those roles.

### On-demand Claude Fable 5 advisor

This is a read-only consultation path, separate from delegation and execution.
Use it only when the user explicitly asks to consult, discuss with, or get an
advisor opinion from Claude Fable 5.

- Send a compact question and only the necessary, non-secret context through
  stdin to `/home/ubuntu/projects/raph-power/codex/claude-fable-advisor.sh`.
- The helper pins `claude-fable-5`, disables tools and session persistence, and
  returns Claude Code's JSON result so the selected model remains auditable.
- For a multi-round discussion, include the prior advisor answer plus the main
  agent's concrete question or disagreement in the next request.
- Treat the response as advisory evidence. The main agent evaluates it, owns
  the final judgment, and performs any implementation or external action.
- If the CLI, authentication, model, quota, or request fails, report the exact
  failure. Do not silently substitute another model or claim consultation.

### Security defaults

- Do NOT auto-approve commands involving credentials/secrets.
- Do NOT embed secrets into delegated prompts or artifacts.
- Security/auth classification still follows the universal classification
  rules; it does not force delegation.

## Project-specific delegation overrides

<!-- Project-specific delegation rules go below this marker. install.sh preserves anything below this line on re-install. -->
