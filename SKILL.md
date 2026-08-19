---
name: wordwall
description: 用自然語言控制 Wordwall 建立互動活動、設定學生作業、抓取作答結果。當使用者說「把這份題目做成 Wordwall 遊戲」「發一個 Wordwall 活動給學生」「幫我在 Wordwall 建 Quiz/轉盤/配對」「看某個 Wordwall 活動的成績」時使用此技能。
---

# Wordwall CLI 技能

透過本資料夾的 `wordwall.py`(一支 Playwright CLI)操作 Wordwall。
**這是 CLI + Skill 模式,不是 MCP server** —— 直接用 PowerShell 呼叫腳本即可。

## 什麼時候用

- 使用者要「把教材/題目變成 Wordwall 互動遊戲」
- 使用者要「把 Wordwall 活動指派給學生、拿分享連結」
- 使用者要「看某活動的學生成績」
- 使用者明確指名要用 Wordwall 的特有範本(轉盤、打地鼠、配對牌…)

> 若使用者只是要「教材變互動小遊戲」而不指定平台,先考慮全域的
> `teaching-minigames` 技能(直接產出可分享 HTML,不必登入、不會被 Wordwall 改版弄壞)。
> 只有非用 Wordwall 特有功能(特定範本、內建成績追蹤、社群庫)時才用本技能。

## 前置作業(每台電腦一次)

```powershell
cd wordwall-cli
.\setup.ps1 -WithPdf
python wordwall.py chrome-login
# 使用者本人在專用 Chrome 登入後
python wordwall.py grab-session
python wordwall.py doctor --login --pdf
```

登入狀態會存到 `~/.wordwall/state.json` 並自動沿用。專用 Chrome 使用
`~/.wordwall/chrome-login-profile` 與預設埠 `9333`。
**絕不要向使用者索取帳號密碼,也不要嘗試自動填入** —— 一律由本人在 Chrome 登入。

## Agent 首次使用流程

1. 在 repo 根目錄執行 `python wordwall.py doctor --pdf`。
2. 若 `doctor` 回報缺少元件，照它列出的命令安裝；Windows 可用 `.\setup.ps1 -WithPdf`。
3. 若尚未登入，執行 `python wordwall.py chrome-login`，請使用者本人在專用 Chrome 登入，再執行 `python wordwall.py grab-session`。不可索取或代填密碼。
4. 執行 `python wordwall.py doctor --login --pdf` 驗證後才進行正式建立／指派／下載。
5. `~/.wordwall/state.json` 是每位使用者自己的 session，不可複製到 repo 或交給他人。

## 使用者指定遊戲時

1. 將需求映射為 `schema`：選擇題=`quiz`、配對=`pair`、分類=`group`、轉盤／卡片=`single`、線索作答=`clue`、標記圖=`diagram`。
2. 判斷媒體型態：`text`、`text-image` 或 `image-image`。
3. 執行 `python wordwall.py recommend --intent "使用者的遊戲名稱" --implemented-only`；必要時加 `--schema`、`--media`。
4. 使用者指名的範本若尚未實作，不得偷偷換範本；應說明並提供相容選項。
5. 建立順序固定為 `--dry-run` → `--editor-check --headless` → 使用者確認 → 正式建立。

在產生內容前先執行：

```powershell
python wordwall.py plan --request "使用者的完整需求"
```

規劃器會輸出範本、素材層級、版面策略、content contract、asset manifest contract 與下一步。
有 JSON 與素材後，用 `--content`、`--assets` 重新執行，兩項預檢都通過才進 editor-check。

## 圖片生成預設

- 優先使用使用者既有圖片或 PDF 截圖。
- Level 3 通過 AI 必要性門檻且需要新圖時，**必須載入 `imagegen` skill 並呼叫
  `image_gen` 內建工具實際產圖**；不得只撰寫 prompt、要求使用者自行產圖，或未說明就改成 Level 2。
- **OpenCode 環境覆寫**：Level 3 一律載入 `draw` skill，使用 Draw 實際產圖；不得在 OpenCode 改用
  `imagegen`／`image_gen`、只撰寫 prompt，或靜默降級。產圖後將
  `generation_method=local-draw-override` 寫入 asset manifest。
- 產圖後必須目視檢查定稿 PNG，再把實際 prompt 與對應方法寫入 asset manifest：
  ChatGPT／Codex 使用 `generation_method=builtin-imagegen`，OpenCode 使用
  `generation_method=local-draw-override`。
- 若 ChatGPT／Codex 沒有 `imagegen`／`image_gen`，或 OpenCode 沒有可載入的 `draw` skill，
  停止 Level 3 建立並請使用者提供圖片或選擇降級；不要求 API key。
- ChatGPT／Codex 不得假設使用者安裝維護者的私人 `draw` 技能或擁有相同本機路徑；
  OpenCode 則依本機 `draw` skill 規則執行。
- 若目前環境另有使用者明確指定的生圖技能，可在本機覆寫，但不可把私人設定寫入 repo。
- 詳見 `docs/IMAGE_GENERATION.md`。
- 三級出題、AI 必要性門檻與創意題型見 `docs/QUESTION_LEVELS.md`。

## 指令對照

| 使用者意圖 | 指令 |
|---|---|
| 診斷核心環境 | `python wordwall.py doctor` |
| 連同登入與 PDF 一起診斷 | `python wordwall.py doctor --login --pdf` |
| 依名稱推薦範本 | `python wordwall.py recommend --intent "圖片配對" --implemented-only` |
| 依結構推薦範本 | `python wordwall.py recommend --schema pair --media image-image --implemented-only` |
| 檢查登入是否有效 | `python wordwall.py check` |
| 查有哪些範本 | `python wordwall.py templates` |
| 驗證文字／圖片題 | `python wordwall.py create --content 內容.json --dry-run` |
| 填入線上編輯器但不發布 | `python wordwall.py create --content 內容.json --editor-check --headless` |
| 建立已支援的 Wordwall 活動 | `python wordwall.py create --content 內容.json --headless` |
| 預檢學生作業 | `python wordwall.py assign --activity-url <網址> --title <名稱> --dry-run --headless` |
| 建立學生作業 | 移除上一指令的 `--dry-run` |
| 列出作業 ID | `python wordwall.py results list --title <名稱> --headless` |
| 預檢成績匯出 | `python wordwall.py results export --assignment-id <ID> --format xlsx --dry-run --headless` |
| 下載 Excel／CSV | 移除上一指令的 `--dry-run` |
| 校正選擇器(改版時) | `python wordwall.py inspect --url <網址>` |
| PDF 整頁截圖 | `python wordwall.py pdf-screenshot --input <PDF> --page 2 --output <PNG>` |
| PDF 區域裁切 | 上一指令加入 `--crop x0,y0,x1,y1` |

## 內容 JSON 格式

見 `examples/quiz_example.json`、`examples/image_quiz_example.json` 與
`examples/matchup_example.json`。
把使用者口述的題目整理成這個結構後,再呼叫 `create`。

圖片題在 item 加入 `"image": "題目.png"`;相對路徑以 JSON 所在資料夾為準。
若截圖已含四個選項,Wordwall 的 `answers` 可填 `A/B/C/D`。

需要圖片選項或圖片配對時，欄位可使用 `{ "text": "...", "image": "..." }`。
配對 schema 見 `examples/matchup_image_example.json`；Quiz 圖片選項見
`examples/quiz_image_answers_example.json`。完整分類見 `docs/TEMPLATE_CAPABILITIES.md`。

分類使用 `examples/group_sort_example.json`；轉盤／隨機卡使用
`examples/single_list_example.json`，轉盤目前只支援 `mode=simple`。
句子填空使用 `examples/complete_sentence_example.json`，以 `{{答案}}` 標記缺口；
目前每頁支援一個缺口，多個缺口要拆成多頁。
True or false、Matching pairs 雙模式與 Labelled diagram 分別見
`examples/true_false_example.json`、`examples/matching_pairs_different_example.json`、
`examples/labelled_diagram_example.json`。

PDF 截圖是選用功能。若 CLI 提示缺少元件，執行：

```powershell
python -m pip install -r requirements-pdf.txt
```

先輸出整頁確認座標，再用 `--crop x0,y0,x1,y1` 裁切；座標單位為 PDF 點。
上傳前必須目視確認題幹、選項、數學符號與幾何圖完整。

## 登入方式

- **首選 `chrome-login` → `grab-session`**：
  1. `python wordwall.py chrome-login`
  2. 使用者本人在專用真實 Chrome 登入 Wordwall(Google 或 Email 皆可)。
  3. `python wordwall.py grab-session`
- `chrome-login` 預設使用本工具專用 profile 與埠 `9333`；埠被占用時會拒絕連線，
  改用 `python wordwall.py chrome-login --port 9334`。不得擅自連接其他工具的 Chrome。
- `login` 只供可互動 PowerShell 使用 Email 登入；非互動終端會在開啟瀏覽器前安全退出，
  Agent 應改走首選流程。
- `grab-session --cdp-url <網址>` 僅供進階使用；必須確認該 Chrome 是使用者本人為此次登入開啟。

## ✅ 目前狀態

- `chrome-login` / `login` / `grab-session` / `check` / `templates` / `inspect`:**已可運作**。
- `doctor` / `pdf-screenshot`:**已可運作**，缺少元件時會給出安裝命令。
- `create`：Quiz 六種、Pair 四種、Group sort、Speed sorting、Speaking cards、
  Spin the wheel／Random wheel 簡易模式、Complete the sentence 均已通過真實編輯器不儲存驗證。
- True or false、Open the box 簡易模式、Rank order、Matching pairs 雙模式與
  Labelled diagram 也已通過文字／圖片真實編輯器不儲存驗證。
- 其他未標示支援的範本仍須先 `inspect` 實測，不得只因 schema 相似就宣稱可用。
- `assign`:已可建立作業並取得學生 `/play/` 連結。
- `results list` / `results export`:已實測可精確選取作業並下載 Excel，不在終端顯示學生姓名。
- 任何指令失敗會自動把截圖與 HTML 存到 `debug/`,拿那個校正選擇器最快。

## 內容編輯頁是固定網址

點範本會導到 `https://wordwall.net/create/entercontent?templateId=<id>`。
template-id 對照見 `wordwall.py` 的 `TEMPLATE_IDS`(quiz=5, match_up=3, group_sort=2, spin_the_wheel=8…)。

## 邊界與注意

- `results` 會碰到**學生個資** —— 執行前提醒使用者確認符合校方規範與 Wordwall 使用條款,不要大量批次抓取。
- 送出/建立/發布這類**不可逆動作**,執行前先向使用者確認內容無誤。
- 真實建立圖片活動前,確認活動名稱、題目圖片與正確答案。
- 真實建立學生作業前,確認作業名稱、姓名／匿名、截止日期及結果顯示設定。
- 成績檔預設放 `%USERPROFILE%\Downloads\wordwall-results`,不得 commit 到 repo。
- Wordwall 改版導致選擇器失效時,用 `inspect` 重新校正,不要硬猜。
