# wordwall-cli（專案藍圖）

> 本檔是跨 Agent 的專案入口。每次開工先讀本檔與 `handoff.md`。

## 專案簡介

以 Python、Playwright 與 Skill，讓 AI Agent 透過自然語言建立及管理 Wordwall 教學活動。目前以 Quiz 建立流程為可用基線，再逐步擴充其他範本、作業指派與成績讀取。

## 關鍵時程

<!-- 尚未指定 -->

## 目標與路線圖

- [x] 建立 CLI、Skill、Windows 安裝腳本與 Quiz JSON 範例
- [x] Quiz 建立流程完成第一版
- [ ] 在目前環境重新實測登入檢查與 Quiz 建立
- [ ] 擴充 Match up 等其他範本
- [ ] 校正 `assign` 作業指派流程
- [ ] 校正 `results` 成績讀取流程

## 專案入口

- `README.md`：功能、狀態與使用方式
- `INSTALL.md`：Windows 教師安裝指南
- `SKILL.md`：AI Agent 操作規則
- `wordwall.py`：Playwright CLI 主程式
- `setup.ps1`：Windows 環境安裝與驗證
- `examples/`：活動內容 JSON 範例
- `handoff.md`：目前狀態與下一步

## 同步層級（本專案初始化至第 3 層級）

| 層級 | 平台 | 位置 | 讀取時機 |
|---|---|---|---|
| L1 | 本地（Google Drive） | `AGENTS.md`＋`handoff.md` | 每個 session |
| L2 | GitHub | https://github.com/mathruffian-dot/wordwall-cli | 指定時 |
| L3 | Obsidian | `2026worldwall/專案工作流程.md` | 有需要時 |

## 固定規則

- 所有回應與專案文件使用繁體中文；Windows 指令使用 PowerShell。
- 不向使用者索取或自動填寫 Wordwall 帳號密碼。
- Wordwall session 只能放在使用者本機的 `%USERPROFILE%\.wordwall\state.json`，不得進入 repo。
- 建立、發布或指派真實活動前，先讓使用者確認題目、答案與活動名稱。
- `results` 涉及學生資料；正式資料只使用班級代號與座號，不儲存學生姓名。
- Wordwall 改版造成選擇器失效時，先用 `inspect` 取得 DOM 與 debug 證據，不憑猜測修改。
- `debug/` 可能含帳號畫面或頁面內容，禁止 commit。
- 開工先讀 `handoff.md`；收工更新 `handoff.md` 與 Obsidian 駕駛艙。
- Google Drive 上的 Git repo 必須維持 `git config windows.appendAtomically false`。
