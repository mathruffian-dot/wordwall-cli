---
name: wordwall
description: 用自然語言控制 Wordwall 建立互動活動、設定學生作業、抓取作答結果。當使用者說「把這份題目做成 Wordwall 遊戲」「發一個 Wordwall 活動給學生」「幫我在 Wordwall 建 Quiz/轉盤/配對」「看某個 Wordwall 活動的成績」時使用此技能。
---

# Wordwall CLI 技能

透過本資料夾的 `wordwall.py`(一支 Playwright CLI)操作 Wordwall。
**這是 CLI + Skill 模式,不是 MCP server** —— 直接用 bash 呼叫腳本即可。

## 什麼時候用

- 使用者要「把教材/題目變成 Wordwall 互動遊戲」
- 使用者要「把 Wordwall 活動指派給學生、拿分享連結」
- 使用者要「看某活動的學生成績」
- 使用者明確指名要用 Wordwall 的特有範本(轉盤、打地鼠、配對牌…)

> 若使用者只是要「教材變互動小遊戲」而不指定平台,先考慮全域的
> `teaching-minigames` 技能(直接產出可分享 HTML,不必登入、不會被 Wordwall 改版弄壞)。
> 只有非用 Wordwall 特有功能(特定範本、內建成績追蹤、社群庫)時才用本技能。

## 前置作業(每台電腦一次)

```bash
cd wordwall-cli
pip install playwright && playwright install chromium
python wordwall.py login      # 開瀏覽器,由使用者本人手動登入(可 Google/Email)
```

登入狀態會存到 `~/.wordwall/state.json` 並自動沿用。過期就再跑一次 `login`。
**絕不要向使用者索取帳號密碼,也不要嘗試自動填入** —— 一律請他自己在 `login` 開的視窗登入。

## 指令對照

| 使用者意圖 | 指令 |
|---|---|
| 檢查登入是否有效 | `python wordwall.py check` |
| 查有哪些範本 | `python wordwall.py templates` |
| 建立活動 | `python wordwall.py create --content 內容.json` |
| 設成學生作業 | `python wordwall.py assign --activity-url <網址>` |
| 抓學生成績 | `python wordwall.py results` |
| 校正選擇器(改版時) | `python wordwall.py inspect --url <網址>` |

## 內容 JSON 格式

見 `examples/quiz_example.json` 與 `examples/matchup_example.json`。
把使用者口述的題目整理成這個結構後,再呼叫 `create`。

## 登入方式(Google 會擋自動化瀏覽器)

Google 會封鎖 Playwright 這類自動化瀏覽器的登入,所以:
- **首選 `grab-session`**:你在真實 Chrome 登入 wordwall.net(除錯埠模式),工具把 session 複製過來。
  1. 完全關閉 Chrome,用除錯埠重開:
     `& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="$env:TEMP\ww-debug"`
     (近版 Chrome 一定要加 `--user-data-dir`,會開一個獨立乾淨視窗)
  2. 在那個 Chrome 登入 wordwall.net。
  3. `python wordwall.py grab-session`
- 次選 `login`:用 Wordwall 自己的 **Email + 密碼**登入(不要點 Sign in with Google)。

## ✅ 目前狀態

- `login` / `grab-session` / `check` / `templates` / `inspect`:**已可運作**。
- `create`(**Quiz 範本**):**已實測可用**,能從 JSON 建出真實活動(2026-07 驗證)。
- `create`(其他範本):選擇器待比照 quiz 補上——先 `inspect --url https://wordwall.net/create/entercontent?templateId=<id>` 取得該編輯頁 DOM,再仿 `_fill_content` 的 quiz 分支補寫。
- `assign` / `results`:仍是佔位,選擇器待校正(標了 `TODO(需實測)`)。
- 任何指令失敗會自動把截圖與 HTML 存到 `debug/`,拿那個校正選擇器最快。

## 內容編輯頁是固定網址

點範本會導到 `https://wordwall.net/create/entercontent?templateId=<id>`。
template-id 對照見 `wordwall.py` 的 `TEMPLATE_IDS`(quiz=5, match_up=3, group_sort=2, spin_the_wheel=8…)。

## 邊界與注意

- `results` 會碰到**學生個資** —— 執行前提醒使用者確認符合校方規範與 Wordwall 使用條款,不要大量批次抓取。
- 送出/建立/發布這類**不可逆動作**,執行前先向使用者確認內容無誤。
- Wordwall 改版導致選擇器失效時,用 `inspect` 重新校正,不要硬猜。
