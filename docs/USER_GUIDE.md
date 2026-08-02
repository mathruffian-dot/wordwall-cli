# Wordwall CLI 使用說明

這份手冊提供給老師、一般使用者，以及協助操作的 Codex／Claude Code 等 Agent。
Wordwall CLI 可以建立互動活動、指派學生作業、匯出作答成績，也能把 PDF 題本裁切成圖片題。

> 本工具不是 Wordwall 官方產品。Wordwall 沒有公開 API，因此工具使用瀏覽器自動化完成操作；網站改版後，部分功能可能需要重新校正。

## 1. 可以做什麼

- 依自然語言需求推薦適合的 Wordwall 範本。
- 建立純文字、文字加圖片、圖片加圖片的活動。
- 把 PDF 整頁或指定範圍輸出成 PNG 題圖。
- 在正式建立前檢查 JSON、圖片路徑、答案與線上編輯器內容。
- 把活動設成學生作業，取得 `/play/` 連結。
- 列出作業並下載 Excel 或 CSV 成績。

目前支援建立的主要類型：

| 類型 | 可用範本或模式 |
|---|---|
| 選擇題 | Quiz、Gameshow quiz、Maze chase、Flying fruit、Airplane、Win or lose quiz |
| 配對 | Match up、Find the match、Flash cards、Balloon pop |
| 分類 | Group sort、Speed sorting |
| 單項清單 | Speaking cards、Spin the wheel／Random wheel 簡易模式 |
| 句子 | Complete the sentence；每頁一個缺口 |
| 固定分組 | True or false |
| 翻牌配對 | Matching pairs，相同／不同物品模式 |
| 其他 | Open the box 簡易模式、Rank order、Labelled diagram |

查看目前版本的完整範本狀態：

```powershell
python wordwall.py templates
```

## 2. 第一次安裝

需要 Windows 10／11、PowerShell、Python 3.10 以上、網路連線及自己的 Wordwall 帳號。

```powershell
git clone https://github.com/mathruffian-dot/wordwall-cli.git
cd wordwall-cli
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup.ps1 -WithPdf
python wordwall.py doctor --pdf
```

不需要 PDF 截圖時可改用 `.\setup.ps1`。`doctor` 會檢查 Python、Playwright、
Chromium、登入狀態及 PDF 元件，缺少元件時會顯示可直接執行的安裝命令。

## 3. 登入自己的 Wordwall

### 方式 A：Wordwall Email 登入

```powershell
python wordwall.py login
```

工具會開啟登入視窗。請使用者本人輸入資料，工具與 Agent 都不應取得帳號密碼。
Google 常會阻擋自動化瀏覽器，因此這個視窗建議使用 Wordwall 的 Email 與密碼登入。

### 方式 B：從真實 Chrome 取得登入狀態

若必須使用 Google 登入：

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 `
  --user-data-dir="$env:TEMP\ww-debug"
```

在新開的 Chrome 登入 Wordwall，再回到 PowerShell 執行：

```powershell
python wordwall.py grab-session
```

確認登入：

```powershell
python wordwall.py check
python wordwall.py doctor --login --pdf
```

登入狀態只存於目前使用者的
`C:\Users\<使用者名稱>\.wordwall\state.json`，請勿傳給別人或放進 GitHub。

## 4. 建立活動的標準流程

每次都依序執行：

```text
規劃範本與素材 → 準備 JSON／圖片 → 本機預檢 → 線上編輯器預覽 → 人工確認 → 正式建立
```

### 步驟 1：用自然語言規劃

```powershell
python wordwall.py plan --request "八年級幾何四選一，題目與選項放在同一張圖片"
```

把規劃結果存成 JSON：

```powershell
python wordwall.py plan `
  --request "用漫畫情境製作四題解謎選擇題" `
  --output "content\comic-quiz-plan.json"
```

規劃器會採用最低足夠層級：

1. 純文字題。
2. PDF、既有題庫或精準圖形的截圖題。
3. 只有故事、漫畫、視覺解謎等需求才使用 AI 生成圖片。

精準幾何、座標圖或統計圖應使用原始題圖或精準繪圖後截圖，不應交給 AI 猜測線段與數值。

### 步驟 2：推薦範本

```powershell
python wordwall.py recommend --intent "圖片配對" --implemented-only

python wordwall.py recommend `
  --schema pair `
  --media image-image `
  --implemented-only
```

媒體型態：

- `text`：純文字。
- `text-image`：文字搭配圖片。
- `image-image`：題目與選項／配對兩端都可用圖片。

### 步驟 3：準備內容 JSON

最基本的 Quiz：

```json
{
  "template": "quiz",
  "title": "整數運算練習",
  "items": [
    {
      "question": "(-3) + 8 = ?",
      "answers": ["-11", "-5", "5", "11"],
      "correct": 2
    }
  ]
}
```

`correct` 從 `0` 開始計算，因此上例的 `2` 代表第三個選項。

圖片題：

```json
{
  "template": "quiz",
  "title": "幾何圖片題",
  "items": [
    {
      "question": "請看圖作答",
      "image": "geometry_question.png",
      "answers": ["A", "B", "C", "D"],
      "correct": 2
    }
  ]
}
```

圖片相對路徑以內容 JSON 所在資料夾為準。若題幹與四個圖形選項已合成一張圖，
Wordwall 選項使用 `A`、`B`、`C`、`D` 即可。題幹、答案或配對兩端也可使用：

```json
{ "text": "可選文字", "image": "圖片.png" }
```

現有範例：

| 需求 | 範例檔 |
|---|---|
| 文字選擇題 | `examples\quiz_example.json` |
| 題幹圖片 | `examples\image_quiz_example.json` |
| 圖片答案 | `examples\quiz_image_answers_example.json` |
| 文字／圖片配對 | `examples\matchup_example.json`、`examples\matchup_image_example.json` |
| 分類 | `examples\group_sort_example.json` |
| 轉盤／卡片 | `examples\single_list_example.json` |
| 句子填空 | `examples\complete_sentence_example.json` |
| 是非題 | `examples\true_false_example.json` |
| 翻牌配對 | `examples\matching_pairs_different_example.json` |
| 標示圖 | `examples\labelled_diagram_example.json` |

### 步驟 4：本機預檢

```powershell
python wordwall.py create `
  --content "examples\quiz_example.json" `
  --dry-run
```

這一步不登入、不開啟 Wordwall，也不建立活動，只檢查 JSON、答案與圖片路徑。

### 步驟 5：線上編輯器預覽

```powershell
python wordwall.py create `
  --content "examples\quiz_example.json" `
  --editor-check `
  --headless
```

工具會填入 Wordwall 編輯器並回讀內容，但不按 Done、不建立活動。
請檢查題名、題目、圖片、選項與正解。

### 步驟 6：正式建立

人工確認後才執行：

```powershell
python wordwall.py create `
  --content "examples\quiz_example.json" `
  --headless
```

這一步會在使用者帳號內建立真實活動。

## 5. 將 PDF 題目做成截圖題

若尚未安裝 PDF 元件：

```powershell
python -m pip install -r requirements-pdf.txt
```

先輸出整頁：

```powershell
python wordwall.py pdf-screenshot `
  --input "C:\題本\數學題本.pdf" `
  --page 2 `
  --output "assets\questions\page2.png"
```

再依整頁畫面決定裁切範圍：

```powershell
python wordwall.py pdf-screenshot `
  --input "C:\題本\數學題本.pdf" `
  --page 2 `
  --crop "55,75,540,215" `
  --scale 3 `
  --padding 16 `
  --output "assets\questions\q01.png"
```

`--crop` 順序為 `x0,y0,x1,y1`，單位是 PDF 點，頁碼從 `1` 開始。
裁切後務必目視確認題幹、選項、數學符號與幾何圖完整。

## 6. 把活動指派成學生作業

先預檢設定：

```powershell
python wordwall.py assign `
  --activity-url "https://wordwall.net/resource/123456" `
  --title "八年級幾何練習" `
  --registration name `
  --deadline 2026-08-31 `
  --deadline-time 23:59 `
  --show-answers `
  --leaderboard `
  --start-again `
  --dry-run `
  --headless
```

確認作業名稱、姓名／匿名、截止時間、答案、排行榜及重新作答設定後，
移除 `--dry-run` 正式建立。完成後會回傳可分享給學生的 `/play/` 連結。

若要關閉選項，可用 `--no-show-answers`、`--no-leaderboard` 或 `--no-start-again`。

## 7. 列出與下載學生成績

成績包含學生資料，下載前請確認符合校方規範及 Wordwall 使用條款。

先找作業 ID：

```powershell
python wordwall.py results list `
  --title "八年級幾何" `
  --headless
```

這一步只列出作業 ID、名稱與作答人數，不顯示學生姓名。

預檢下載目標：

```powershell
python wordwall.py results export `
  --assignment-id 123456 `
  --format xlsx `
  --output "C:\成績\八年級幾何" `
  --dry-run `
  --headless
```

`--dry-run` 只確認目標，不下載學生資料。確認後移除 `--dry-run` 正式下載。
也可以用唯一的作業名稱片段代替 ID：

```powershell
python wordwall.py results export `
  --title "八年級幾何練習" `
  --format csv `
  --output "C:\成績\八年級幾何.csv" `
  --headless
```

未指定 `--output` 時，預設下載至
`%USERPROFILE%\Downloads\wordwall-results`。請勿將成績檔放進 GitHub repo。

## 8. 給 Agent 的自然語言說法

- 「把這十題做成 Wordwall Quiz，先預覽，不要發布。」
- 「把這份 PDF 的第一到第五題裁成圖片，再做成四選一活動。」
- 「用圖片配圖片的方式建立配對遊戲。」
- 「把這個活動指派到八月三十一日，學生要輸入姓名，先 dry-run。」
- 「列出名稱含八年級幾何的作業，不要讀學生姓名。」
- 「確認後把作業 ID 123456 的成績下載成 Excel。」

Agent 應遵守：

- 不索取、代填或記錄密碼。
- 不分享或提交 session。
- 建立活動與作業前先預檢並取得確認。
- 下載成績前先確認目標，且不把學生資料放進 repo。
- 未支援的範本不可偷偷替換成別的範本。

## 9. 常見問題

| 問題 | 處理方式 |
|---|---|
| 找不到 `python` | 安裝 Python 3.10 以上並勾選 Add Python to PATH，重開 PowerShell。 |
| 裝過 Playwright 仍顯示缺少 | 用 `(Get-Command python).Source` 確認是同一個 Python，再重跑 `.\setup.ps1`。 |
| Google 說瀏覽器不安全 | 改用 Wordwall Email，或用 Chrome 除錯埠搭配 `grab-session`。 |
| `9222` 連不上 | 完全關閉 Chrome，再用除錯埠與新的 `--user-data-dir` 重開。 |
| 登入過期 | 重新執行 `login` 或 `grab-session`。 |
| 缺少 PDF 元件 | 執行 `.\setup.ps1 -WithPdf` 或安裝 `requirements-pdf.txt`。 |
| 圖片路徑找不到 | 相對路徑以內容 JSON 所在資料夾為準。 |
| Wordwall 編輯器欄位失效 | 網站可能改版；使用 `inspect` 與 `debug` 證據重新校正。 |
| 成績名稱符合多筆 | 先用 `results list` 找唯一作業 ID，再用 `--assignment-id`。 |

## 10. 安全與資料位置

| 資料 | 預設位置 | 可提交 GitHub |
|---|---|---|
| Wordwall session | `%USERPROFILE%\.wordwall\state.json` | 不可 |
| 成績匯出 | `%USERPROFILE%\Downloads\wordwall-results` | 不可 |
| 錯誤畫面／HTML | repo 的 `debug\` | 不可，可能含帳號畫面 |
| 題目 JSON／公開題圖 | `content\`、`assets\` 或 `examples\` | 確認無個資與版權疑慮後才可 |

## 11. 查詢指令說明

任何指令都可以加 `--help`：

```powershell
python wordwall.py --help
python wordwall.py create --help
python wordwall.py assign --help
python wordwall.py results export --help
```

更詳細的安裝資訊見 `INSTALL.md`；範本能力見 `docs\TEMPLATE_CAPABILITIES.md`；
圖片策略見 `docs\QUESTION_LEVELS.md` 與 `docs\IMAGE_GENERATION.md`。
