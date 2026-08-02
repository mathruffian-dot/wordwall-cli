# Wordwall CLI + Skill

用 CLI 的方式(不是 MCP server)讓 Codex、Claude Code 或其他 Agent 操作
[Wordwall](https://wordwall.net)。每位使用者在自己的電腦安裝，並登入自己的帳號；repo 不包含任何帳密或 session。

第一次使用請先閱讀：[完整使用說明](docs/USER_GUIDE.md)；只需要安裝步驟可閱讀
[安裝指南](INSTALL.md)。

視覺化操作網站：[Wordwall CLI 使用指南](https://mathruffian-dot.github.io/wordwall-cli/)

## 為什麼是 CLI + Skill 而不是 MCP?

Wordwall 既沒有公開 API、也沒有官方 CLI,只能靠瀏覽器自動化(Playwright)。
把這套自動化包成「一支 CLI 腳本 + 一頁 Skill 說明」,比包成 MCP server 更適合單人、本機、自己用的情境:

- 不必跑常駐 server、不走 MCP 協定
- 工具定義不佔 Claude 的 context(用到才讀 SKILL.md)
- 改壞了只要改 `wordwall.py` 這一支
- Claude Code 或 Codex 直接用 PowerShell 呼叫

## 最快開始（Windows PowerShell）

```powershell
git clone https://github.com/mathruffian-dot/wordwall-cli.git
cd wordwall-cli
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup.ps1 -WithPdf
python wordwall.py chrome-login
# 在開啟的真實 Chrome 由本人登入 Wordwall
python wordwall.py grab-session
python wordwall.py doctor --login --pdf
```

不需要 PDF 截圖時可只執行 `.\setup.ps1`。`chrome-login` 會使用專用的
`~/.wordwall/chrome-login-profile` 與預設埠 `9333`，不會誤連 NotebookLM 等工具的 Chrome。

> 安全：本工具不會、也看不到你的帳號密碼。登入只在使用者本機的真實 Chrome 進行；
> session 只存於該使用者電腦的 `~/.wordwall/state.json`，不得放入 GitHub。

## Agent 首次執行規則

Agent 拿到 repo 後，先執行：

```powershell
python wordwall.py doctor --pdf
```

若缺少套件，`doctor` 會列出可直接執行的安裝命令。安裝完成但尚未登入時，Agent 應執行
`python wordwall.py chrome-login`，請使用者本人在專用 Chrome 登入，再執行
`python wordwall.py grab-session`；不可索取、代填或記錄帳號密碼。登入完成後再執行：

```powershell
python wordwall.py doctor --login --pdf
```

## 指令

| 指令 | 狀態 | 說明 |
|---|---|---|
| `doctor [--login] [--pdf]` | ✅ 可運作 | 診斷 Python、Playwright、Chromium、本人登入與 PDF 選用元件 |
| `chrome-login` | ✅ 可運作 | 以專用 profile 與安全埠開啟真實 Chrome，供本人登入 |
| `grab-session` | ✅ 可運作 | 只從本工具記錄的 Chrome 複製登入狀態 |
| `login` | ✅ 可運作 | 僅供可互動 PowerShell 使用 Email 登入；非互動終端會安全退出 |
| `check` | ✅ 可運作 | 檢查登入是否有效 |
| `templates` | ✅ 可運作 | 列出支援的範本代號 |
| `recommend` | ✅ 可運作 | 依遊戲名稱、schema 與媒體型態推薦範本 |
| `plan --request "..."` | ✅ 可運作 | 自然語言選型、三級素材決策與內容／素材預檢 |
| `inspect --url <網址>` | ✅ 可運作 | 登入後 dump 頁面 DOM,用來校正選擇器 |
| `create --content x.json` | ✅ 可運作 | 建立 Quiz、配對、分類、簡易轉盤／卡片與句子填空 |
| `create --content x.json --dry-run` | ✅ 可運作 | 只驗證 JSON、答案與圖片路徑 |
| `create --content x.json --editor-check` | ✅ 可運作 | 填入 Wordwall 編輯器並回讀，但不按 Done |
| `pdf-screenshot` | ✅ 可運作 | 將 PDF 整頁或指定區域渲染為題目 PNG |
| `assign --activity-url <網址>` | ✅ 已實測 | 設成學生作業、取得學生連結 |
| `results list` | ✅ 可運作 | 列出作業 ID、名稱與作答人數,不讀學生姓名 |
| `results export` | ✅ 已實測 | 匯出指定作業的 Excel / CSV |

## PDF 截圖題

PDF 功能是選用元件。若尚未安裝，CLI 會提示：

```powershell
python -m pip install -r requirements-pdf.txt
```

輸出整頁 PNG：

```powershell
python wordwall.py pdf-screenshot `
  --input "C:\題本.pdf" --page 2 `
  --output "assets\questions\page2.png"
```

裁切指定區域（座標單位為 PDF 點，順序為 `x0,y0,x1,y1`）：

```powershell
python wordwall.py pdf-screenshot `
  --input "C:\題本.pdf" --page 2 `
  --crop "55,75,540,215" `
  --output "assets\questions\q01.png"
```

先輸出整頁確認座標，再裁切；建立 Wordwall 前仍須目視確認題幹、圖形與選項完整。

## 圖片題

每一題可用 `image` 指定 PNG、JPG 等本機圖片。相對路徑以 JSON 所在資料夾為準:

```json
{
  "template": "quiz",
  "title": "幾何圖片題",
  "items": [{
    "question": "請看圖作答",
    "image": "geometry_question.png",
    "answers": ["A", "B", "C", "D"],
    "correct": 2
  }]
}
```

先 dry-run,確認後再建立:

```powershell
python wordwall.py create --content examples\image_quiz_example.json --dry-run
python wordwall.py create --content examples\image_quiz_example.json --headless
```

Quiz 的題幹及每個答案、Pair 的左右兩端，都能使用共用媒體物件：

```json
{ "text": "可選文字", "image": "圖片.png" }
```

目前已可建立的家族：

- `quiz`：Quiz、Gameshow quiz、Maze chase、Flying fruit、Airplane、Win or lose quiz。
- `pair`：Match up、Find the match、Flash cards、Balloon pop。
- `group`：Group sort、Speed sorting。
- `single`：Speaking cards、Spin the wheel／Random wheel 的簡易模式。
- `cloze`：Complete the sentence；用 `{{答案}}` 標記，每頁目前支援一個缺口。
- `fixed_group`：True or false。
- `pair_mode`：Matching pairs 的相同物品與不同物品兩種模式。
- `single` 擴充：Open the box 簡易模式、Rank order。
- `diagram`：Labelled diagram，使用 0 到 1 的 `x/y` 座標定位 pin。

對應範例：`examples/group_sort_example.json`、`examples/single_list_example.json`、
`examples/complete_sentence_example.json`。

## 圖片生成預設

公開 repo 預設使用 **ChatGPT 訂閱方案內建生圖**，不要求 API key，也不依賴某個
維護者電腦上的私人技能。已有題庫圖片或 PDF 時優先使用原素材；需要新圖時由 Agent
使用所在 ChatGPT／Codex 環境的 `imagegen` skill／`image_gen` 內建工具實際產圖。
Level 3 不得只留下 prompt 或靜默改用截圖；若環境沒有內建生圖工具，必須停下來請
使用者提供圖片或確認降級。完整規則見
[docs/IMAGE_GENERATION.md](docs/IMAGE_GENERATION.md)。

## 自然語言與三級出題規劃

```powershell
python wordwall.py plan --request "用 AI 生圖製作漫畫解謎選擇題"

python wordwall.py plan `
  --request "幾何圖形選擇題，選項只能用圖片判別" `
  --content examples\image_quiz_example.json `
  --assets examples\asset_manifest_screenshot.json
```

規劃器會採用最低足夠層級：純文字、截圖或 AI 生成圖片。第三級只有故事、漫畫、
解謎、多視角、遮擋、影子／倒影、狀態變化等創意必要需求才會通過；精準幾何或座標圖
會降回截圖。完整規格見 [docs/QUESTION_LEVELS.md](docs/QUESTION_LEVELS.md)。

完整範本分類與後續開發狀態見 [docs/TEMPLATE_CAPABILITIES.md](docs/TEMPLATE_CAPABILITIES.md)。

## 指派作業

```powershell
python wordwall.py assign `
  --activity-url "https://wordwall.net/resource/123456" `
  --title "八年級幾何練習" `
  --registration name `
  --deadline 2026-08-31 `
  --deadline-time 23:59 `
  --dry-run --headless
```

確認設定後移除 `--dry-run`,CLI 會建立作業並回傳學生 `/play/` 連結。

## 成績匯出

```powershell
# 先找作業 ID
python wordwall.py results list --title "八年級幾何" --headless

# dry-run 只確認目標,不下載學生資料
python wordwall.py results export --assignment-id 123456 `
  --format xlsx --output "C:\成績\八年級幾何" --dry-run --headless

# 確認後移除 --dry-run
```

預設輸出在 `%USERPROFILE%\Downloads\wordwall-results`。不要把成績檔放進 repo。

## 邊界

- Wordwall 的**遊戲畫面本身**(轉盤動畫、拖曳等)是 canvas / 複雜 JS,本工具**不碰**——
  只自動化「建立活動 / 發作業 / 讀成績」這類管理型操作,那才是價值所在。
- `results` 會碰到**學生個資**,使用前確認符合校方規範與 Wordwall 使用條款。
- 送出、發布等不可逆動作,執行前先確認內容。
- 圖片題在手機上可能縮小;一題一張、裁切緊密,並保留可讀字級。
- Wordwall 改版造成選擇器失效時,用 `inspect` 重新校正;失敗證據會存到已忽略的 `debug/`。

## 檔案結構

```
wordwall-cli/
├── wordwall.py              # CLI 主程式
├── SKILL.md                 # 給 Claude Code 的技能說明(何時/如何呼叫)
├── requirements.txt
├── requirements-pdf.txt     # PDF 截圖選用元件
├── setup.ps1                # Windows 安裝器，可加 -WithPdf / -Login
├── README.md
├── examples/
│   ├── quiz_example.json    # Quiz 內容格式範例
│   ├── image_quiz_example.json
│   ├── geometry_question.png
│   └── matchup_example.json # Match up 內容格式範例
├── tests/                   # 不登入 Wordwall 的單元測試
└── debug/                   # 選擇器失敗時的截圖/HTML(自動產生)
```
