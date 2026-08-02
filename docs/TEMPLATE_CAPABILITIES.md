# Wordwall 範本能力分類

本表依 2026-08-02 登入後的 Wordwall 建立頁唯讀盤點。Wordwall 改版或帳號方案不同時，
以 `python wordwall.py templates --json` 與實際編輯器為準。

| schema | 內容結構 | 圖片能力 | 代表範本 | CLI 建立器 |
|---|---|---|---|---|
| `quiz` | 題幹＋多個答案＋正解 | 題幹與每個答案皆可獨立放圖 | Quiz、Gameshow quiz、Maze chase、Flying fruit、Airplane、Win or lose quiz | 已完成 |
| `pair` | 左端＋右端 | 左右兩端皆可獨立放圖 | Match up、Find the match、Flash cards、Balloon pop | 已完成 |
| `pair_mode` | 相同項目或左右不同項目 | 每個項目皆可附圖 | Matching pairs | 兩種模式皆已完成 |
| `group` | 分類＋分類項目 | 分類與項目可放圖 | Group sort、Speed sorting | 已完成 |
| `fixed_group` | 固定真／假兩組 | 每個敘述可附圖 | True or false | 已完成 |
| `single` | 單一項目清單 | 每個項目可附圖 | Speaking cards、Rank order | 已完成 |
| `single_mode` | 單項目或切換成問答 | 簡易模式每項可附圖 | Spin the wheel、Open the box | 簡易模式已完成；問答模式待開發 |
| `clue` | 線索＋文字／數字答案 | 線索端可放圖 | Complete the sentence | 每頁一個缺口已完成；其他 clue 範本待開發 |
| `word` | 單字＋選用線索 | 線索模式可放圖 | Anagram、Hangman、Wordsearch、Spell the word | 待開發 |
| `diagram` | 底圖＋標籤與 0..1 座標 | 底圖與標籤都可放圖 | Labelled diagram | 已完成 |
| `text` | 純文字項目 | 不支援圖片 | Word magnets | 待開發 |
| `generator` | Wordwall 內建設定 | 不接受一般題目 JSON | Maths generator | 待開發 |

## 共用媒體物件

任何可放圖片的欄位統一使用：

```json
{
  "text": "可省略的文字",
  "image": "相對於 JSON 的圖片路徑"
}
```

字串仍可直接使用，等同只有 `text`：

```json
"三角形"
```

## 分組、單項與缺字格式

分組使用 `groups`，每組包含 `title` 與 `items`：

```json
{"groups": [{"title": "質數", "items": ["2", "3", "5"]}]}
```

轉盤／隨機卡使用單層 `items`。轉盤目前固定 `"mode": "simple"`：

```json
{"mode": "simple", "items": ["說出一個質數", "畫一個三角形"]}
```

Complete the sentence 以 `{{答案}}` 標記缺口；目前每頁支援一個缺口，
多個缺口請拆成多頁：

```json
{"pages": [{"sentence": "三角形內角和是{{180度}}。", "wrong_answers": ["90度"]}]}
```

True or false 的每題使用布林 `correct`。Matching pairs 使用 `mode=same` 搭配
`items`，或 `mode=different` 搭配 `pairs`。

Labelled diagram 必須有底圖與至少三個標籤；`x`、`y` 是相對於底圖的 0 到 1 座標：

```json
{"image": "diagram.png", "labels": [{"text": "頂點 A", "x": 0.2, "y": 0.3}]}
```

## Agent 選型流程

1. 從使用者語句判斷互動：`quiz`、`pair`、`group`、`single`、`clue`、`word`、`diagram`。
2. 判斷媒體：`text`、`text-image`、`image-image`。
3. 執行 `python wordwall.py recommend --schema <schema> --media <media> --implemented-only`。
4. 使用者指定確切範本時優先採用；若建立器尚未完成，不得靜默換成別的遊戲。
5. 依序執行 `--dry-run`、`--editor-check`；使用者確認後才正式建立。

Wordwall 的外觀可以切換，但內容結構不一定能互換。簡單清單不能無損轉成問答，
純文字單字遊戲也不一定接受圖片或特殊數學符號。
