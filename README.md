# Gateway

Caddy reverse proxy，統一管理所有服務的對外路由。

## 架構

```
raphtools.com
├── /poly/simulation       → localhost:8501  (Streamlit)
├── /poly/nothing-happens  → localhost:8502  (Streamlit)
├── /poly/tracker          → localhost:3001  (Next.js)
├── /maple-kit             → localhost:4173  (Vite build)
└── /maple-kit/api         → localhost:8000  (FastAPI)
```

## 常用指令

```bash
caddy reload --config Caddyfile   # 重載設定（不中斷連線）
caddy validate --config Caddyfile # 驗證語法
sudo systemctl restart caddy      # 重啟服務
sudo journalctl -fu caddy         # 即時日誌（含 TLS 憑證申請）
```

## 新增服務

1. 在 `Caddyfile` 加入 handle 區塊：
   ```
   handle /your-path* {
       reverse_proxy localhost:PORT
   }
   ```
2. 確認服務端已設好 base path（詳見各專案 README）
3. `caddy reload --config Caddyfile`
4. 更新 `CLAUDE.md` 的 Service Registry

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
| `maple-toolkit-api` | 8000 | FastAPI (uvicorn) |
| `maple-toolkit-frontend` | 4173 | Vite preview |
| `polymarket-address-tracker` | 3001 | Next.js |
| `polymarket-simulation` | 8501 | Streamlit (app.py) |
| `polymarket-nothing-happens` | 8502 | Streamlit (nothing_happens.py) |

健康檢查：

```bash
bash scripts/check-services.sh
```
