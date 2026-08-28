# AGENTS.md (gateway)
<!-- raph-power-managed: v1 -->

This project follows the raph-power workflow protocols. Codex loads this file at session start; Claude Code consumes the same governance via the raph-power skills/.

## Entry gates

Load only the two protocols needed to classify and start a task:

@/home/ubuntu/projects/raph-power/shared/mistakes-protocol.md
@/home/ubuntu/projects/raph-power/shared/classification.md

## On-demand workflow

Do not preload these files. Read one only when its trigger fires or the active
classification chain calls for it:

@/home/ubuntu/projects/raph-power/shared/hard-gate-template.md
@/home/ubuntu/projects/raph-power/shared/delegation.md
@/home/ubuntu/projects/raph-power/shared/root-cause-gate.md
@/home/ubuntu/projects/raph-power/shared/git-discipline.md
@/home/ubuntu/projects/raph-power/shared/review-gates.md

## Sub-agent workflows

If a task uses a sub-agent workflow, also consult `AGENTS.delegation.md` in this project (installed alongside this file).
If the user explicitly asks to consult or discuss with Claude Fable 5, also
consult that file and follow its on-demand advisor workflow.

## Project-specific

<!-- Project-specific rules go below this marker. install.sh preserves anything below this line on re-install. -->
