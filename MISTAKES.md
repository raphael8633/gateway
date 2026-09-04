# MISTAKES.md — gateway

Routing / upstream 接入時會踩的坑，跨專案適用。單一專案自己的 bug 記在該專案的 MISTAKES.md。Maintained via `/raph-mistakes`。

## Entry Template

### G-XXX <short title>
- Trigger:
- Symptom:
- Guard:
- Verification:

## Active Entries

### G-001 Vite preview 擋掉 gateway 轉進來的 Host header
- Trigger: 新增以 `vite preview` 跑的前端路由（raph-reader 5174、raph-tools 5175 都踩過），只設了 `base`，沒設 `preview.allowedHosts`
- Symptom: `curl 127.0.0.1:PORT/path/` 正常，但外站每個請求都回 `Blocked request. This host ("raphtools.com") is not allowed. To allow this host, add "raphtools.com" to preview.allowedHosts in vite.config.js`；service 是 active、healthz 正常，看起來像 gateway 壞掉
- Guard: 專案 `vite.config.ts` 的 `preview` 區塊固定含 `allowedHosts: ['raphtools.com']`；`Caddyfile` snippet 註解、`README.md` 新增服務步驟、`CLAUDE.md`、`../PLATFORM.md` §2.1 皆已標註。將來加 alias domain 時要同步補進每個 Vite 專案的 `allowedHosts`
- Verification: `curl -s -o /dev/null -w '%{http_code}' -H 'Host: raphtools.com' http://127.0.0.1:PORT/path/` → 200（未修前 403）
