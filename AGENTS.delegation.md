# AGENTS.delegation.md (gateway)
<!-- raph-power-managed-delegation: v1 -->

This file applies only when a Codex session is using a sub-agent / delegation workflow.
If no delegation is in use, stop here and return to `AGENTS.md`.

## Universal delegation rules

@/home/ubuntu/projects/raph-power/shared/delegation.md

The above defines: when to delegate, executor routing by classification, main-context vs sub-agent split, progress logging, prompt packaging, and review gates. Apply it as written.

## Codex-specific notes

### Tool availability check (once per session)

- `codex --version`
- `claude --version`

Record in checkpoint: `codex_cli_version=...`, `claude_cli_version=...` (or `unavailable`).

### Executor routing (Codex perspective)

| Classification | Primary Executor | Fallback |
|---------------|------------------|----------|
| S0 | Main session direct | — |
| S1 | Codex sub-agent (sonnet-equivalent) | — |
| S2 / S3 | Claude Opus via Claude CLI | Codex sub-agent (MUST notify user) |

### Claude CLI dispatch (S2/S3)

Evidence files: prompt at `/tmp/opus-task.md`, raw output at `/tmp/opus-output.txt`.

```bash
claude -p \
  --model claude-opus-4-6 \
  --output-format text \
  < /tmp/opus-task.md \
  > /tmp/opus-output.txt
```

Prompt preamble (Opus must emit raw unified diff):

```
You are a code-generation sub-agent. Produce ONLY a unified diff. Rules:
- First line of your output MUST be `diff --git` or `---`. Nothing before it.
- Do NOT wrap output in markdown code fences. Raw diff only.
- Do NOT output prose, explanation, narration, or XML/JSON.
- If you cannot produce a valid diff, output exactly: MALFORMED
```

### Fallback

If `claude --version` fails or Claude CLI fails the same task twice → notify user, run via Codex sub-agent with `executor=codex-subagent-fallback`.

### Security defaults

- Do NOT auto-approve commands involving credentials/secrets.
- Do NOT embed secrets into `/tmp/*-task.md`.
- If a task involves permissions/auth/security → force `task_class >= S2`, route to Opus.

## Project-specific delegation overrides

<!-- Project-specific delegation rules go below this marker. install.sh preserves anything below this line on re-install. -->
