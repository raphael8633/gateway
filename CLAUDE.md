# CLAUDE.md — PROJECT RULES

## Entry Point

`/raph-core` is enforced via raph-power plugin hook (UserPromptSubmit) — no manual reminder needed.

## Quick Commands

- **reload:** `caddy reload --config Caddyfile`
- **start:** `caddy run --config Caddyfile`
- **validate:** `caddy validate --config Caddyfile`
- **gen-index:** `python3 gen-index.py`
- **watch:** `systemctl status gateway-watch` (systemd 服務，開機自動啟動)
- **build:** N/A
- **test:** N/A
- **lint:** `caddy validate --config Caddyfile`

## Project Context

- **Domain:** `raphtools.com` (Caddy auto-HTTPS / Let's Encrypt; no Cloudflare API required)
- 需維護的檔案：`Caddyfile`（routing）；`www/index.html` 由 `gen-index.py` 自動生成，勿手動編輯
- **新增服務流程：**
  1. `Caddyfile` 加 handle 區塊 → `caddy reload`（watcher 自動觸發）
  2. `../README.md` 加一列並填 `Gateway` 欄 → `www/index.html` 自動更新（watcher 自動觸發）
- 若 `gateway-watch.service` 異常，手動執行：`python3 gen-index.py` 重生成 index.html
- **`www/index.html` source of truth：** `../README.md` 的 `Gateway` 欄（見 workspace CLAUDE.md 格式說明）
- Streamlit 服務需加 `--server.baseUrlPath=<path>` 啟動參數才能正確處理靜態資源
- Next.js 服務需在 `next.config.js` 設 `basePath`
- FastAPI 服務需設 `root_path` 或掛在 sub-application

## Service Registry

| Path | Port | Project | Type |
|------|------|---------|------|
| `/auth` | 9091 | global-auth | Authelia (SSO portal) |
| `/poly/simulation` | 8501 | polymarket-simulation | Streamlit |
| `/poly/nothing-happens` | 8502 | polymarket-simulation | Streamlit |
| `/poly/tracker` | 3001 | polymarket-address-tracker | Next.js [protected] |
| `/health` | 3002 | health-manage | Next.js [protected] |
| `/task-hub` | 3003 | task-hub (planned) | — [protected] |
| `/maple-kit` | 4173 | maple-toolkit | Vite/FastAPI |
| `/maple-kit/api` | 8000 | maple-toolkit | FastAPI |
| `/vpn` | 8011 | vps2-vpn | FastAPI (uvicorn) |
| `/public` | 8020 | public-share | Python WSGI |

## Notes

- raph-power plugin provides: task classification (S0-S3), TDD, verification, review gates, git discipline, debugging, subagent delegation, mistake tracking
- This file should only contain project-specific rules and quick commands
- MISTAKES.md is maintained per-project with entries specific to this codebase
