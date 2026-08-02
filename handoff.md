# 開發交接

## 已完成

- Windows 安裝器與 `doctor` 環境診斷。
- 使用者本人 `login`，以及真實 Chrome 的 `grab-session`。
- 文字／圖片 Quiz 建立，並驗證正式 `/resource/` 網址。
- 學生作業建立與 `/play/` 連結。
- My Results 清單與 Excel 成績匯出。
- PDF 整頁／區域截圖；依賴未安裝時顯示明確安裝指令。
- 範本能力目錄、中文別名與 `recommend` 推薦指令。
- Group sort／Speed sorting、Speaking cards、簡易轉盤與 Complete the sentence 建立器。
- Complete the sentence 以 `{{答案}}` 標記，每頁目前支援一個缺口。
- True or false、Open the box、Rank order、Matching pairs 雙模式與 Labelled diagram 建立器。
- 公開生圖預設為 ChatGPT 訂閱方案內建能力；repo 不要求 API key 或私人 draw 技能。
- `plan` 自然語言規劃器：三級素材決策、AI 必要性門檻、content／asset manifest 預檢。
- `quiz` 家族共用建立器：題幹及答案選項皆支援圖片。
- `pair` 家族共用建立器：左右兩端皆支援圖片。
- `create --editor-check`：填入真實編輯器並回讀，但不發布。

## 尚未完成

- `group`、`single`、`clue`、`word`、`diagram` 建立器仍待開發。
- Wordwall 非公開 API，網站改版後可能需要更新 Playwright 選擇器。
- CSV 匯出程式路徑已完成，但應持續以不含敏感資料的作業做回歸驗證。

## 接手檢查

```powershell
python wordwall.py doctor --login --pdf
python -m py_compile wordwall.py
python -m unittest discover -s tests -v
```

不要提交 `~/.wordwall/state.json`、`debug/` 或學生成績檔。
