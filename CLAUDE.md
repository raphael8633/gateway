# CLAUDE.md — PROJECT RULES

## Entry Point

`/raph-core` is enforced via raph-power plugin hook (UserPromptSubmit) — no manual reminder needed.

## Quick Commands

- **reload:** `caddy reload --config Caddyfile`
- **start:** `caddy run --config Caddyfile`
- **validate:** `caddy validate --config Caddyfile`
- **build:** N/A
- **test:** N/A
- **lint:** `caddy validate --config Caddyfile`

## Project Context

- **Domain:** `raphtools.com` (Cloudflare DNS-01 TLS via `CF_API_TOKEN`)
- 這是純 Caddy 設定專案，唯一需要維護的檔案是 `Caddyfile`
- 新增服務：在 Caddyfile 加 handle 區塊 → 確認服務設好 base path → `caddy reload`
- Streamlit 服務需加 `--server.baseUrlPath=<path>` 啟動參數才能正確處理靜態資源
- Next.js 服務需在 `next.config.js` 設 `basePath`
- FastAPI 服務需設 `root_path` 或掛在 sub-application

## Service Registry

| Path | Port | Project | Type |
|------|------|---------|------|
| `/poly/simulation` | 8501 | polymarket-simulation | Streamlit |
| `/poly/nothing-happens` | 8502 | polymarket-simulation | Streamlit |
| `/poly/tracker` | 3000 | polymarket-address-tracker | Next.js |
| `/maple-kit` | 4173 | maple-toolkit | Vite/FastAPI |
| `/maple-kit/api` | 8000 | maple-toolkit | FastAPI |

## Notes

- raph-power plugin provides: task classification (S0-S3), TDD, verification, review gates, git discipline, debugging, subagent delegation, mistake tracking
- This file should only contain project-specific rules and quick commands
- MISTAKES.md is maintained per-project with entries specific to this codebase
