# 開發交接

## ⏯️ 目前做到哪

- Wordwall CLI 的安裝、本人登入、活動建立、作業指派、成績匯出及 PDF 截圖流程已完成。
- 已支援 Quiz、Pair、Group、Single、Complete the sentence、True or false、
  Open the box、Rank order、Matching pairs 與 Labelled diagram 等已驗證範本。
- `plan` 已能依自然語言決定範本、三級素材策略，並預檢 content 與 asset manifest。
- 給一般使用者的文字手冊與視覺化網站已完成。
- GitHub Pages：https://mathruffian-dot.github.io/wordwall-cli/
- GitHub PR #1 已合併至 `master`。

## 🚦 目前狀態

- CLI Python 語法檢查通過。
- 27 項單元測試全部通過。
- 視覺化網站已通過桌面、390×844 手機尺寸與互動分頁測試。
- 公開網址實測回應 HTTP 200。
- 本機 `assets/`、`content/` 是會考題目素材，未加入公開 repo。
- AGENTS.md 未登記 Obsidian 專案駕駛艙；本次未建立 L3 專案紀錄。

## ➡️ 下一步

1. 在另一台乾淨 Windows 電腦實測 `git clone`、`setup.ps1 -WithPdf`、本人登入與 `doctor`。
2. 開發題目與圖片素材的完整編排流程：產生／截圖、合成、manifest、預檢與建立活動。
3. 依實際教學需求繼續驗證尚未支援的 Wordwall 範本，不以相似 schema 直接宣稱可用。

## ⚠️ 注意事項

- 不得提交 `~/.wordwall/state.json`、`debug/`、成績、Cookie 或 Token。
- `assets/`、`content/` 可能含考卷題目；公開前逐一確認版權與使用目的。
- Google 登入優先使用真實 Chrome 搭配 `grab-session`；不可向使用者索取密碼。
- Git 操作曾因背景 diff／fsmonitor 出現 `packed-refs.lock` 提示，但 PR 與合併成功；
  若再發生，先確認 Git 程序，不要直接強制刪除鎖檔。

## 🕐 最後更新

- 時間：2026-08-02 21:00（Asia/Taipei）
- 更新者：Codex @ 三師爸SENSEBAR
- Git push：待推
