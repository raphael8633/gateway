---
id: M-001
title: Vite preview blocks the Host header forwarded by the gateway (legacy G-001)
severity: hard
triggers:
  keywords:
  - vite preview
  - preview.allowedHosts
  - Blocked request
  - 新增路由
  - new upstream
  files:
  - vite.config.ts
  - Caddyfile
guard:
  command: 'curl -s -o /dev/null -w ''%{http_code}'' -H ''Host: raphtools.com'' http://127.0.0.1:PORT/path/  #
    must be 200; vite.config preview.allowedHosts must include raphtools.com'
status: active
occurred:
- '2026-09-12'
---

## Symptom
`curl 127.0.0.1:PORT/path/` 正常，但外站每個請求都回 `Blocked request. This host ("raphtools.com") is not allowed…`；service active、healthz 正常，看起來像 gateway 壞掉。raph-reader 5174、raph-tools 5175 都踩過。

## Resolution
專案 `vite.config.ts` 的 `preview` 區塊固定含 `allowedHosts: ['raphtools.com']`；`Caddyfile` snippet 註解、`README.md` 新增服務步驟、`CLAUDE.md`、`../PLATFORM.md` §2.1 皆已標註。將來加 alias domain 時要同步補進每個 Vite 專案的 `allowedHosts`。
