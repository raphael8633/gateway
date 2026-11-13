# Gateway

Caddy reverse proxy，`raphtools.com` 所有服務的對外入口。

## 架構

完整 path → port 對照表見 [`CLAUDE.md` Service Registry](CLAUDE.md#service-registry)（由 `gen-service-registry.py` 自動生成）。

- Routing 由 `Caddyfile` 定義，受保護路由統一用 `import proxy_auth PORT` snippet；路由是否受保護以 `Caddyfile` 為準（搜 `import proxy_auth`）
- Auth 由獨立的 [global-auth](../global-auth/) 專案處理（Authelia + forward_auth）
- 沒有對應 handle 的路徑一律回 404
- TLS 憑證由 Caddy 自動向 Let's Encrypt 申請與續期（HTTP-01／TLS-ALPN-01），存在 `~/.local/share/caddy/certificates/`；機器上沒有 certbot 與 nginx

## 常用指令

```bash
caddy validate --config Caddyfile       # 驗證語法
caddy reload --config Caddyfile         # 重載設定（不中斷連線；gateway-watch 會在存檔時自動執行）
sudo systemctl restart caddy            # 重啟服務
sudo journalctl -fu caddy               # 即時日誌（含 TLS 憑證申請）
python3 gen-index.py                    # 手動重新生成 www/index.html
python3 -m pytest -q tests              # 測試
systemctl status gateway-watch          # file watcher 狀態
systemctl status platform-backup.timer  # 平台本機備份排程
```

因為 gateway-watch 一存檔就 reload，改 Caddyfile 時先在副本上 `caddy validate --adapter caddyfile --config <副本>`，通過再覆蓋回來。

## 自動生成

`watch.sh`（`gateway-watch.service`）監看兩個檔：

| 檔案 | 觸發動作 |
|------|---------|
| `../README.md` | `gen-index.py` → `www/index.html`；`gen-service-registry.py` → `CLAUDE.md` registry |
| `Caddyfile` | `caddy reload`；`gen-service-registry.py` |

`../README.md` 的專案表由 `readme_table.py` 統一解析（`Gateway` 欄＝導覽頁卡片，`Systemd Service` 欄＝狀態燈的 unit，標「（user）」的走 user manager），三支腳本共用。`www/index.html` 與 registry 是產生物，勿手改；樣式改 `www/index.template.html`。

導覽頁的狀態燈來自 `scripts/services-status.py`（`gateway-services-status.service`，:8030）。健康檢查由 raph-vps-state 的 self-check 負責：`web:<path>` probe 逐條打路由（含 gate 有沒有漏），結果進晨報。

## Access log 與每週統計

- Caddy 把 `raphtools.com` 的請求寫成 JSON lines 到 `~/data/caddy/access.log`（50MiB 輪替、留 20 份、最多 90 天）。Cookie 與 Authorization 由 Caddy 遮蔽；只另外抄出 watcher 的 `locale` cookie 值，用來算 en 介面比例。
- `scripts/access_stats.py` 每週一 07:20 台北由 raph-platform 的 `gateway-access-stats` job 執行，輸出一行 🟢 進 07:30 晨報，並追加一筆到 `~/data/caddy/weekly.jsonl`。
- 分類：人類頁面瀏覽＝外部瀏覽器的 document 載入或 Next.js RSC 導覽（不含 prefetch）且 2xx／304；其他瀏覽器請求（靜態檔、API、被導去登入）；機器（非瀏覽器 UA、bot、4xx／5xx）；本機瀏覽器（本機 IP 的真瀏覽器導覽，Shadowsocks 用戶從這台出去，另列一格）；本機健檢（其他本機請求與 `vps-sweep/1`）。`/tao-conviction` 另分子頁與 en 數。
- 純 client 端互動靠 beacon：watcher 在 `/emission` 試算器第一次展開時送 `GET /tao-conviction/api/beacon?e=simulator-open`（204），統計只計 `EVENT_LABELS` 白名單內的 `e`（路由公開，其他名稱一律不進晨報），列在晨報的「事件」；新增事件時在 `EVENT_LABELS` 加中文名。白名單事件仍可被刻意灌量，數字是上限。其他不發請求的互動量不到。

## 基線回應標頭

Caddy 對全站回應補四個預設標頭：`Strict-Transport-Security`（`max-age=86400`）、`X-Content-Type-Options: nosniff`、`Referrer-Policy: strict-origin-when-cross-origin`、`X-Frame-Options: SAMEORIGIN`。每個都用 `?`，上游沒送才補，所以服務或 Authelia 自己送的值會保留。四個標頭各寫一條 `header` 指令：寫在同一個區塊時，Caddy 只在四個都不存在時才套用整組。CSP 由各服務自己負責。新服務若要被別的網域嵌入，自己送 `X-Frame-Options` 或 CSP `frame-ancestors`。

## 新增服務

1. 在 `Caddyfile` 加 handle 區塊（公開：`reverse_proxy localhost:PORT`；受保護：`import proxy_auth PORT`），validate 後存檔
2. 確認服務端已設好 base path（見下表）
3. 受保護路由在 `../global-auth/config/configuration.yml` 加 ACL；`tests/test_acl_routes.py` 會擋下對不到 forward_auth 路由的 ACL
4. 在 `../README.md` 加一列並填 `Gateway` 與 `Systemd Service` 欄 → 導覽頁與 registry 自動更新

| 框架 | Base path 設定 |
|------|---------|
| Next.js | `next.config.js` → `basePath: '/your-path'` |
| FastAPI | `app = FastAPI(root_path="/your-path")` |
| Vite (prod) | `vite.config.ts` → `base: '/your-path'` ＋ `preview.allowedHosts: ['raphtools.com']`（缺後者＝整站 `Blocked request`，`.mistakes/M-001`） |
| Streamlit | `streamlit run app.py --server.baseUrlPath=/your-path` |

## 安裝與 systemd

Caddy 用 apt 套件（`/usr/bin/caddy`），更新走 `sudo apt-get install --only-upgrade caddy`。套件預設讀 `/etc/caddy/Caddyfile`；`deploy/caddy-override.conf` 是 drop-in，裝到 `/etc/systemd/system/caddy.service.d/override.conf`，讓 Caddy 以 `ubuntu` 身分讀本 repo 的 `Caddyfile`：

```bash
sudo install -D -m 644 deploy/caddy-override.conf /etc/systemd/system/caddy.service.d/override.conf
sudo systemctl daemon-reload && sudo systemctl restart caddy
```

其他 unit 在 `deploy/`：`gateway-watch.service`、`gateway-services-status.service`、`platform-backup.{service,timer}`；`journald-limit.conf` 對應 `/etc/systemd/journald.conf.d/limit.conf`（`SystemMaxUse=1G`）。後端服務的 unit 名見 `../README.md` 的 `Systemd Service` 欄。

## Platform Maintenance

本機滾動備份：`scripts/platform-backup.sh`，由 `platform-backup.timer` 每日 04:30 台北執行；異地上傳、時效監看與還原演練在 raph-vps-state。

## 與 global-auth 的關係

Auth 由 [global-auth](../global-auth/)（Authelia）處理，刻意不合併進此 repo：

- **職責分離**：gateway＝routing（Caddy）；global-auth＝identity（Authelia）
- **操作語意不同**：gateway 用 `caddy reload` 熱重載；global-auth 需 `systemctl restart`（Authelia 不支援 SIGHUP）
- **機密邊界**：global-auth `.env` 含 secret；本 repo 是 public，不放任何 secret
- **整合契約**：Caddyfile `forward_auth 127.0.0.1:9091`
