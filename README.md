# Gateway

Caddy reverse proxy，統一管理所有服務的對外路由。

## 架構

```
raphtools.com
├── /auth                  → localhost:9091  (Authelia — global-auth)   [SSO portal]
├── /poly/simulation       → localhost:8501  (Streamlit)
├── /poly/nothing-happens  → localhost:8502  (Streamlit)
├── /poly/tracker          → localhost:3001  (Next.js)                  [protected]
├── /maple-kit             → localhost:4173  (Vite build)
├── /maple-kit/api         → localhost:8000  (FastAPI)
├── /vpn                   → localhost:8011  (FastAPI — vps2-vpn)
├── /health                → localhost:3002  (Next.js — health-manage)  [protected]
├── /task-hub              → localhost:3003  (planned)                  [protected]
└── /public                → localhost:8020  (Python WSGI — public-share)
```

## 常用指令

```bash
caddy reload --config Caddyfile   # 重載設定（不中斷連線）
caddy validate --config Caddyfile # 驗證語法
sudo systemctl restart caddy      # 重啟服務
sudo journalctl -fu caddy         # 即時日誌（含 TLS 憑證申請）
python3 gen-index.py              # 手動重新生成 www/index.html
systemctl status gateway-watch    # file watcher 狀態（systemd，開機自動啟動）
```

## 導覽頁（www/index.html）

`www/index.html` 由 `gen-index.py` 從 `../README.md` 的 `Gateway` 欄**自動生成**，勿手動編輯。

啟動 watcher 後，更改 `../README.md` 或 `Caddyfile` 會自動觸發對應動作：

| 檔案 | 觸發動作 |
|------|---------|
| `../README.md` | `gen-index.py` → 更新 `www/index.html` |
| `Caddyfile` | `caddy reload` |

## 新增服務

1. 在 `Caddyfile` 加入 handle 區塊：
   ```
   handle /your-path* {
       reverse_proxy localhost:PORT
   }
   ```
2. 確認服務端已設好 base path（詳見各專案 README）
3. `caddy reload --config Caddyfile`（watcher 啟動中則自動執行）
4. 在 `../README.md` 加一列並填 `Gateway` 欄 → `www/index.html` 自動更新
5. 更新 `CLAUDE.md` 的 Service Registry

目前已註冊的 Next.js 專案有：

- `/poly/tracker` → `polymarket-address-tracker`（port 3001）
- `/health` → `health-manage`（port 3002，`NEXT_PUBLIC_BASE_PATH=/health`）

## 各語言 Base Path 設定

| 框架 | 設定方式 |
|------|---------|
| Streamlit | `streamlit run app.py --server.baseUrlPath=/your-path` |
| Next.js | `next.config.js` → `basePath: '/your-path'` |
| FastAPI | `app = FastAPI(root_path="/your-path")` |
| Vite (prod) | `vite.config.ts` → `base: '/your-path'` |

## 初次安裝 / 更新 Caddy binary

```bash
bash setup.sh
```

TLS 憑證由 Caddy 自動透過 Let's Encrypt（HTTP-01 / TLS-ALPN-01）申請與更新，無需 Cloudflare API。

## Systemd 設定

Caddy 以 systemd 服務方式運行，override 指向此 repo 的 Caddyfile 並以 `ubuntu` 用戶執行：

```ini
# /etc/systemd/system/caddy.service.d/override.conf
[Service]
User=ubuntu
Group=ubuntu
ExecStart=
ExecStart=/usr/bin/caddy run --config /home/ubuntu/projects/gateway/Caddyfile
ExecReload=
ExecReload=/usr/bin/caddy reload --config /home/ubuntu/projects/gateway/Caddyfile --force
```

### 後端服務 Systemd Services

所有後端服務均設 `Restart=on-failure`，開機自動啟動：

| Service 名稱 | Port | 說明 |
|-------------|------|------|
| `global-auth` | 9091 | Authelia SSO portal (`/auth`, forward_auth gate) |
| `maple-toolkit-api` | 8000 | FastAPI (uvicorn) |
| `maple-toolkit-frontend` | 4173 | Vite preview |
| `polymarket-address-tracker` | 3001 | Next.js |
| `health-manage` | 3002 | Next.js (體重管理 MVP, base path `/health`) |
| `task-hub` | 3003 | planned — wired, service not yet deployed |
| `public-share` | 8020 | Python WSGI (`/public`, html/md file share) |
| `polymarket-simulation` | 8501 | Streamlit (app.py) |
| `polymarket-nothing-happens` | 8502 | Streamlit (nothing_happens.py) |
| `vps2-vpn` | 8011 | FastAPI (uvicorn, /home/ubuntu/projects/vps2-vpn) |

健康檢查：

```bash
bash scripts/check-services.sh
```
