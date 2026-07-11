# Wordwall CLI + Skill

用 CLI 的方式(不是 MCP server)讓 Claude Code 用自然語言操作 [Wordwall](https://wordwall.net)。

## 為什麼是 CLI + Skill 而不是 MCP?

Wordwall 既沒有公開 API、也沒有官方 CLI,只能靠瀏覽器自動化(Playwright)。
把這套自動化包成「一支 CLI 腳本 + 一頁 Skill 說明」,比包成 MCP server 更適合單人、本機、自己用的情境:

- 不必跑常駐 server、不走 MCP 協定
- 工具定義不佔 Claude 的 context(用到才讀 SKILL.md)
- 改壞了只要改 `wordwall.py` 這一支
- Claude Code 直接用 bash 呼叫

## 安裝(每台電腦一次)

```bash
cd wordwall-cli
pip install -r requirements.txt
playwright install chromium
python wordwall.py login      # 開瀏覽器,你「自己」手動登入(Google 或 Email 皆可)
```

> 安全:本工具不會、也看不到你的帳號密碼。`login` 只是開一個瀏覽器視窗讓你本人登入,
> 再把登入後的 session 存到 `~/.wordwall/state.json` 重複使用。過期就再跑一次 `login`。

## 指令

| 指令 | 狀態 | 說明 |
|---|---|---|
| `login` | ✅ 可運作 | 手動登入並存 session(用 Wordwall Email 登入,勿用 Google) |
| `grab-session` | ✅ 可運作 | 從真實 Chrome(除錯埠)複製登入,繞過 Google 對自動化的封鎖 |
| `check` | ✅ 可運作 | 檢查登入是否有效 |
| `templates` | ✅ 可運作 | 列出支援的範本代號 |
| `inspect --url <網址>` | ✅ 可運作 | 登入後 dump 頁面 DOM,用來校正選擇器 |
| `create --content x.json` | ✅ Quiz 已實測 | 依內容 JSON 建活動(quiz 已跑通;其他範本待補) |
| `assign --activity-url <網址>` | 🔧 待校正 | 設成學生作業、拿分享連結 |
| `results` | 🔧 待校正 | 抓學生作答結果 |

## 目前狀態:骨架已成,選擇器待「登入實測」

**能跑的部分現在就能跑**(login / check / templates / inspect)。

`create` / `assign` / `results` 這三個依賴「登入後編輯畫面」的指令,其 DOM 選擇器
**尚未校正**(程式裡標了 `TODO(需實測)`),因為那些畫面藏在登入牆後面,沒有登入的
session 拿不到真實結構。要讓它們真的能動,做一次校正即可:

```bash
python wordwall.py login                                   # 1. 手動登入
python wordwall.py inspect --url https://wordwall.net/create   # 2. dump 建立頁 DOM
# 3. 依 dump 出來的元素,校正 wordwall.py 裡 _click_template / _fill_content / _save_and_get_url
# 4. 先把 quiz 範本跑通,再擴充其他範本
```

失敗時,腳本會自動把截圖與 HTML 存到 `debug/`,拿那個對照校正選擇器最快。

## 邊界

- Wordwall 的**遊戲畫面本身**(轉盤動畫、拖曳等)是 canvas / 複雜 JS,本工具**不碰**——
  只自動化「建立活動 / 發作業 / 讀成績」這類管理型操作,那才是價值所在。
- `results` 會碰到**學生個資**,使用前確認符合校方規範與 Wordwall 使用條款。
- 送出、發布等不可逆動作,執行前先確認內容。

## 檔案結構

```
wordwall-cli/
├── wordwall.py              # CLI 主程式
├── SKILL.md                 # 給 Claude Code 的技能說明(何時/如何呼叫)
├── requirements.txt
├── README.md
├── examples/
│   ├── quiz_example.json    # Quiz 內容格式範例
│   └── matchup_example.json # Match up 內容格式範例
└── debug/                   # 選擇器失敗時的截圖/HTML(自動產生)
```
