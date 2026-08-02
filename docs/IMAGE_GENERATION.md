# 圖片生成預設

本 repo 的公開預設是使用 **ChatGPT／Codex 內建的 `imagegen` skill 與
`image_gen` 圖片生成工具**。
使用者不需要提供 OpenAI API key，也不需要安裝特定的第三方或本機生圖腳本。

## Agent 處理順序

1. 優先使用使用者已有的題庫圖片、PDF 截圖或自行提供的素材。
2. Level 3 通過 AI 必要性門檻後，載入 `imagegen` skill 並呼叫 `image_gen` 工具實際產圖。
3. 不得只產生 prompt、要求使用者自行操作，或在未說明的情況下改用 Level 2 截圖。
4. 產圖後目視檢查數學內容、答案洩漏、文字可讀性與構圖，再保存定稿 PNG。
5. 把 PNG 路徑放入 Wordwall JSON 的 `image` 欄位，並在 asset manifest 保存實際 prompt
   與 `generation_method=builtin-imagegen`。
6. 執行 `--dry-run` 與 `--editor-check`，確認圖片真的可讀、可上傳。
7. 使用者確認後才正式建立 Wordwall 活動。

三級出題門檻、整張題圖、圖片配對與素材 manifest 規格見
[`QUESTION_LEVELS.md`](QUESTION_LEVELS.md)。

## 沒有內建生圖能力時

Agent 必須暫停 Level 3 建立，清楚說明目前無法呼叫內建生圖工具，並請使用者提供圖片
或明確確認降級為 Level 2。不得把「只寫 prompt」標示為已完成 Level 3。
不得要求使用者把 API key 寫進 repo，也不得把 session、金鑰或私人技能路徑提交到 GitHub。

## 本機覆寫

維護者可以在自己的電腦設定其他生圖技能；這屬於本機工作流，不是 repo 安裝需求。
公開文件與範例不可假設其他使用者也擁有相同技能。
