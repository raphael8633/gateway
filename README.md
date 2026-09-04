# Gateway

Caddy reverse proxy，統一管理所有服務的對外路由。

## 架構

完整 path → port 對照表見 [`CLAUDE.md` Service Registry](CLAUDE.md#service-registry)（由 `gen-service-registry.py` 自動生成）。

- Routing 由 `Caddyfile` 定義，受保護路由統一用 `import proxy_auth PORT` snippet
- Auth 邏輯由獨立的 [global-auth](../global-auth/) 專案處理（Authelia + forward_auth）
- 路由是否受保護以 `Caddyfile` 為準（搜 `import proxy_auth`）

## 常用指令

```bash
caddy reload --config Caddyfile   # 重載設定（不中斷連線）
caddy validate --config Caddyfile # 驗證語法
sudo systemctl restart caddy      # 重啟服務
sudo journalctl -fu caddy         # 即時日誌（含 TLS 憑證申請）
python3 gen-index.py              # 手動重新生成 www/index.html
systemctl status gateway-watch    # file watcher 狀態（systemd，開機自動啟動）
systemctl status platform-backup.timer # 平台本機備份排程
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
2. 確認服務端已設好 base path（詳見各專案 README）。Vite `vite preview` 前端還要設 `preview.allowedHosts: ['raphtools.com']`，否則外站每個請求都回 `Blocked request. This host is not allowed`（`MISTAKES.md` G-001）
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
| Vite (prod) | `vite.config.ts` → `base: '/your-path'` ＋ `preview.allowedHosts: ['raphtools.com']`（缺後者 = 整站 `Blocked request`） |

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

所有後端服務均設 `Restart=on-failure`，開機自動啟動。Path → port 對應見 [CLAUDE.md Service Registry](CLAUDE.md#service-registry)；systemd unit 名稱見 workspace `../README.md` 的 `Systemd Service` 欄。

健康檢查：

```bash
bash scripts/check-services.sh
```

`scripts/check-services.sh` 會從 `Caddyfile` 解析 handle/import/reverse_proxy port，不需手動維護 port 清單。

## Platform Maintenance

- 本機滾動備份：`scripts/platform-backup.sh`，由 `platform-backup.timer` 每日 04:30 Asia/Taipei 執行。
- journald 上限：`deploy/journald-limit.conf` 對應 `/etc/systemd/journald.conf.d/limit.conf`，設定 `SystemMaxUse=1G`。

## 與 global-auth 的架構關係

Auth 邏輯由獨立的 [global-auth](../global-auth/) 專案（Authelia）處理，刻意不合併進此 repo。原因：

- **職責分離**：`gateway` = routing layer（Caddy）；`global-auth` = identity layer（Authelia）
- **操作語意不同**：gateway 用 `caddy reload` 熱重載；global-auth 需 `systemctl restart`（M-003：Authelia 不支援 SIGHUP）
- **機密邊界**：global-auth `.env` 含 JWT secret；gateway config 無敏感資料，分開可獨立審計
- **整合契約**：Caddyfile `forward_auth 127.0.0.1:9091`，跨越此邊界不需要共用 codebase
