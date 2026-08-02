# 圖片生成預設

本 repo 的公開預設是使用 **ChatGPT 訂閱方案內建的圖片生成能力**。
使用者不需要提供 OpenAI API key，也不需要安裝特定的第三方或本機生圖腳本。

## Agent 處理順序

1. 優先使用使用者已有的題庫圖片、PDF 截圖或自行提供的素材。
2. 需要全新插圖時，使用 Agent 所在 ChatGPT／Codex 環境的內建圖片生成能力。
3. 產圖後保存為 PNG，再把檔案路徑放進 Wordwall JSON 的 `image` 欄位。
4. 執行 `--dry-run` 與 `--editor-check`，確認圖片真的可讀、可上傳。
5. 使用者確認後才正式建立 Wordwall 活動。

三級出題門檻、整張題圖、圖片配對與素材 manifest 規格見
[`QUESTION_LEVELS.md`](QUESTION_LEVELS.md)。

## 沒有內建生圖能力時

Agent 應請使用者提供圖片，或引導使用者在其 ChatGPT 介面產圖後下載 PNG。
不得要求使用者把 API key 寫進 repo，也不得把 session、金鑰或私人技能路徑提交到 GitHub。

## 本機覆寫

維護者可以在自己的電腦設定其他生圖技能；這屬於本機工作流，不是 repo 安裝需求。
公開文件與範例不可假設其他使用者也擁有相同技能。
