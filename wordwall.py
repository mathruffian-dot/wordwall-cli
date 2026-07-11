#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wordwall CLI —— 讓 Claude Code 用自然語言控制 Wordwall。

設計理念:這是一支「CLI 工具」,不是 MCP server。
Claude Code 透過 bash 呼叫它,搭配同資料夾的 SKILL.md 就知道何時、怎麼用。
好處:不佔 context、無常駐 server、改壞了只要改這一支腳本(詳見 README.md)。

分工:
  ● 已可運作(不依賴登入後畫面):login / check / templates / inspect
  ● 需登入實測校正選擇器(已用「TODO(需實測)」標出):create / assign / results
    這些指令會盡力執行,失敗時自動把截圖與 DOM 存到 debug/ 供校正,不會靜默失敗。

安全:本腳本「絕不」處理你的帳號密碼。login 指令會開一個瀏覽器視窗,
      由你「自己手動登入」(可用 Google 或 Email),再把登入後的 session 存下來重複使用。
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# ---- 路徑設定 ----
CONFIG_DIR = Path.home() / ".wordwall"
STATE_FILE = CONFIG_DIR / "state.json"          # 登入後的 session(cookies 等)
DEBUG_DIR = Path(__file__).resolve().parent / "debug"
BASE = "https://wordwall.net"

# ---- Wordwall 30+ 範本(2026-07 首頁實測抓到的清單) ----
TEMPLATES = {
    "quiz": "Quiz — 多選題,點正確答案進入下一題",
    "match_up": "Match up — 把關鍵字拖到對應的定義",
    "flash_cards": "Flash cards — 正面提示、背面答案的字卡",
    "speaking_cards": "Speaking cards — 從洗好的牌堆隨機發牌",
    "spin_the_wheel": "Spin the wheel — 轉盤隨機抽出項目",
    "group_sort": "Group sort — 把項目拖進正確的分組",
    "complete_the_sentence": "Complete the sentence — 把字詞拖進句子空格",
    "find_the_match": "Find the match — 點掉配對的答案直到清空",
    "unjumble": "Unjumble — 拖曳字詞重組成正確句子",
    "anagram": "Anagram — 拖動字母重組單字",
    "open_the_box": "Open the box — 依序點開盒子揭曉內容",
    "matching_pairs": "Matching pairs — 翻牌配對",
    "gameshow_quiz": "Gameshow quiz — 有計時與加分的多選題",
    "true_or_false": "True or false — 判斷對錯,限時快答",
    "random_wheel": "Random wheel — 隨機轉盤",
    "labelled_diagram": "Labelled diagram — 把標籤拖到圖上正確位置",
    "maze_chase": "Maze chase — 迷宮追逐,跑向正確答案",
    "hangman": "Hangman — 猜字母",
    "wordsearch": "Wordsearch — 找字遊戲",
    "crossword": "Crossword — 填字遊戲",
}

# 範本代號 -> Wordwall 的 data-template-id(2026-07 從建立頁實測抓到,用 ID 點最穩)
TEMPLATE_IDS = {
    "quiz": 5, "match_up": 3, "flash_cards": 76, "speaking_cards": 70,
    "spin_the_wheel": 8, "group_sort": 2, "complete_the_sentence": 36,
    "find_the_match": 46, "unjumble": 72, "anagram": 38, "open_the_box": 30,
    "matching_pairs": 25, "gameshow_quiz": 69, "true_or_false": 35,
    "labelled_diagram": 22, "maze_chase": 49, "hangman": 73, "wordsearch": 10,
    "crossword": 11, "random_wheel": 8,
    # 其餘實測到的範本(如需可再補進 TEMPLATES 說明):
    "rank_order": 50, "watch_and_memorize": 23, "image_quiz": 68,
    "balloon_pop": 71, "flip_tiles": 75, "win_or_lose_quiz": 78,
    "spell_the_word": 79, "speed_sorting": 81, "flying_fruit": 82,
    "type_the_answer": 89, "type_the_number": 83, "airplane": 48,
    "whack_a_mole": 45, "word_magnets": 47, "maths_generator": 59,
}


def die(msg: str, code: int = 1):
    """印錯誤訊息並結束。"""
    print(f"[錯誤] {msg}", file=sys.stderr)
    sys.exit(code)


def _need_playwright():
    """延遲載入 Playwright,給出友善的安裝提示。"""
    try:
        from playwright.sync_api import sync_playwright  # noqa
        return sync_playwright
    except ImportError:
        die("尚未安裝 Playwright。請執行:\n"
            "    pip install playwright\n"
            "    playwright install chromium")


def _context(p, headless: bool = True):
    """開一個「已登入」的瀏覽器 context。需先跑過 login。"""
    if not STATE_FILE.exists():
        die("尚未登入。請先執行:  python wordwall.py login")
    browser = p.chromium.launch(headless=headless)
    ctx = browser.new_context(storage_state=str(STATE_FILE))
    return browser, ctx


def _verify_logged_in(page) -> bool:
    """導到只有登入才看得到的頁面,確認 session 還有效。"""
    page.goto(f"{BASE}/myactivities", wait_until="domcontentloaded")
    url = page.url
    if "login" in url or "accounts.google.com" in url or url.rstrip("/") == BASE:
        return False
    return True


def _dump_debug(page, name: str):
    """任何選擇器失敗時,把截圖與頁面文字存下來,方便校正選擇器。"""
    DEBUG_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    png = DEBUG_DIR / f"{name}_{ts}.png"
    html = DEBUG_DIR / f"{name}_{ts}.html"
    try:
        page.screenshot(path=str(png), full_page=True)
        html.write_text(page.content(), encoding="utf-8")
        print(f"[debug] 已存截圖與 HTML 供選擇器校正:\n  {png}\n  {html}", file=sys.stderr)
    except Exception as e:  # noqa
        print(f"[debug] 存 debug 檔失敗:{e}", file=sys.stderr)


# ======================================================================
# 指令:login —— 已可運作
# ======================================================================
def cmd_login(args):
    """開瀏覽器讓「使用者本人」手動登入,再把 session 存起來重複使用。"""
    sync_playwright = _need_playwright()
    CONFIG_DIR.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 一定要有頭,讓你看得到登入畫面
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(f"{BASE}/", wait_until="domcontentloaded")
        print("=" * 60)
        print("請在剛開啟的瀏覽器視窗『手動登入』Wordwall。")
        print("⚠️ 請用『Email + 密碼』登入,不要點『Sign in with Google』——")
        print("   Google 會封鎖自動化瀏覽器的登入。若你的帳號只有 Google,")
        print("   請先在登入頁用『Forgot password』設一組密碼,或改用 grab-session。")
        print("(本程式不會、也看不到你的密碼)")
        print("登入完成、看到你的活動清單後,回到這個終端機按 Enter……")
        print("=" * 60)
        input()
        ctx.storage_state(path=str(STATE_FILE))
        print(f"[完成] 已把登入狀態存到:{STATE_FILE}")
        print("之後其他指令會自動沿用這個登入,不必再登。過期了再跑一次 login 即可。")
        browser.close()


# ======================================================================
# 指令:grab-session —— 已可運作(繞過 Google 對自動化瀏覽器的封鎖)
# ======================================================================
def cmd_grab_session(args):
    """從『你已登入的真實 Chrome』複製 Wordwall 登入狀態,存成本工具的 session。

    這條路不自動化登入,所以 Google 不會擋。步驟:
      1. 完全關閉所有 Chrome 視窗。
      2. 用除錯埠重開 Chrome(PowerShell):
         & "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222
      3. 在那個 Chrome 裡確定已登入 wordwall.net(平常怎麼登都行,含 Google)。
      4. 執行:python wordwall.py grab-session
    """
    sync_playwright = _need_playwright()
    CONFIG_DIR.mkdir(exist_ok=True)
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(args.cdp_url)
        except Exception as e:  # noqa
            die(f"連不上你的 Chrome({args.cdp_url})。\n"
                f"     請先『完全關閉 Chrome』,再用除錯埠重開:\n"
                f'     & "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222\n'
                f"     原始錯誤:{e}", code=4)
        if not browser.contexts:
            die("連上了 Chrome,但找不到任何分頁 context。請確認 Chrome 有開著網頁。", code=4)
        ctx = browser.contexts[0]
        # 確認這個 context 真的有 wordwall 的登入(用一個分頁去 myactivities 驗)
        page = ctx.new_page()
        logged_in = _verify_logged_in(page)
        page.close()
        if not logged_in:
            die("在你的 Chrome 裡沒偵測到 Wordwall 登入。\n"
                "     請先在那個 Chrome 分頁登入 wordwall.net,再重跑本指令。", code=5)
        ctx.storage_state(path=str(STATE_FILE))
        print(f"[完成] 已從你的 Chrome 複製 Wordwall 登入狀態到:{STATE_FILE}")
        print("現在可以關掉那個除錯用的 Chrome 了。之後 inspect / create 都會沿用這個登入。")


# ======================================================================
# 指令:check —— 已可運作
# ======================================================================
def cmd_check(args):
    """檢查目前存的登入 session 是否還有效。"""
    sync_playwright = _need_playwright()
    with sync_playwright() as p:
        browser, ctx = _context(p, headless=True)
        page = ctx.new_page()
        ok = _verify_logged_in(page)
        browser.close()
    if ok:
        print("[OK] 登入有效,可以正常操作。")
    else:
        die("登入已失效或過期,請重新執行:  python wordwall.py login", code=2)


# ======================================================================
# 指令:templates —— 已可運作
# ======================================================================
def cmd_templates(args):
    """列出支援的 Wordwall 範本代號。"""
    print("可用的範本代號(建活動時用 --template 或寫在內容 JSON 的 template 欄):\n")
    for key, desc in TEMPLATES.items():
        print(f"  {key:<24} {desc}")


# ======================================================================
# 指令:inspect —— 已可運作(這是「登入實測」的橋樑)
# ======================================================================
def cmd_inspect(args):
    """登入後導到指定頁面,把可互動元素 dump 出來 —— 用來校正下面幾個指令的選擇器。

    用法範例:
        python wordwall.py inspect --url https://wordwall.net/create
    """
    sync_playwright = _need_playwright()
    with sync_playwright() as p:
        browser, ctx = _context(p, headless=args.headless)
        page = ctx.new_page()
        if not _verify_logged_in(page):
            browser.close()
            die("登入已失效,請先重新 login。", code=2)
        page.goto(args.url, wait_until="networkidle")
        page.wait_for_timeout(1500)
        _dump_debug(page, "inspect")
        # 額外列出所有帶文字的按鈕 / 輸入框,方便肉眼挑選擇器
        elems = page.eval_on_selector_all(
            "button, a[role=button], input, textarea, [contenteditable=true]",
            """els => els.slice(0, 120).map(e => ({
                tag: e.tagName.toLowerCase(),
                type: e.getAttribute('type') || '',
                text: (e.innerText || e.value || e.placeholder || '').trim().slice(0, 40),
                id: e.id || '',
                cls: (e.className || '').toString().slice(0, 40),
                data_testid: e.getAttribute('data-testid') || ''
            }))""",
        )
        print(json.dumps(elems, ensure_ascii=False, indent=2))
        browser.close()


# ======================================================================
# 指令:create —— TODO(需實測):選擇器待登入後校正
# ======================================================================
def cmd_create(args):
    """依內容 JSON 建立一個 Wordwall 活動。

    內容 JSON 範例見 examples/。基本結構:
        { "template": "quiz", "title": "...", "items": [...] }
    """
    content = json.loads(Path(args.content).read_text(encoding="utf-8"))
    template = content.get("template") or args.template
    if not template:
        die("內容 JSON 未指定 template,也沒給 --template。")
    if template not in TEMPLATES:
        die(f"未知範本:{template}(用 `templates` 指令查可用清單)")

    sync_playwright = _need_playwright()
    with sync_playwright() as p:
        browser, ctx = _context(p, headless=args.headless)
        page = ctx.new_page()
        if not _verify_logged_in(page):
            browser.close()
            die("登入已失效,請先重新 login。", code=2)
        try:
            page.goto(f"{BASE}/create", wait_until="networkidle")
            # ---- TODO(需實測)開始:以下選擇器需用 `inspect` 對照真實 DOM 校正 ----
            # 1) 選範本:Wordwall 建立頁的範本卡片。實測後改成正確選擇器,例如:
            #    page.get_by_role("link", name="Quiz").click()
            _click_template(page, template)
            # 2) 填標題與內容(不同範本欄位不同,見 _fill_content)
            _fill_content(page, content)
            # 3) 儲存 / 建立,取得活動網址
            url = _save_and_get_url(page)
            # ---- TODO(需實測)結束 ----
            print(f"[完成] 已建立活動:{url}")
        except Exception as e:  # noqa
            _dump_debug(page, "create_fail")
            die(f"建立活動時選擇器對不上(很可能是 Wordwall 改版或尚未校正)。\n"
                f"     請用 `inspect --url {BASE}/create` 取得真實 DOM 再校正 _click_template / _fill_content。\n"
                f"     原始錯誤:{e}", code=3)
        finally:
            browser.close()


def _click_template(page, template: str):
    """在建立頁點選指定範本卡片(已實測:用 data-template-id 最穩)。"""
    tid = TEMPLATE_IDS.get(template)
    if tid is None:
        raise ValueError(f"沒有 {template} 的 template-id 對照,請先補進 TEMPLATE_IDS。")
    card = page.locator(f'.template.js-item[data-template-id="{tid}"]')
    card.wait_for(state="visible", timeout=15000)
    card.click()
    page.wait_for_load_state("networkidle")


def _fill_content(page, content: dict):
    """把題目內容填進 Wordwall 編輯器(選擇器已於 2026-07 對 Quiz 編輯頁實測)。

    Quiz 頁結構:
      input.js-activity-title      —— 活動標題
      .quiz-item                   —— 每一題的容器
        .js-question-box .js-item-input   —— 題幹(contenteditable)
        .answer-box .js-item-input        —— 每個答案(contenteditable)
        .js-question-check                —— 每個答案前的「標正解」切換鈕
      文字「Add more answers」/「Add a question」—— 加答案 / 加題目
      button.js-done-button        —— 完成
    """
    template = content.get("template")
    title = content.get("title", "")
    if title:
        page.locator("input.js-activity-title").fill(title)

    if template == "quiz":
        items = content.get("items", [])
        if not items:
            raise ValueError("quiz 內容沒有任何題目(items 為空)。")
        for qi, item in enumerate(items):
            if qi > 0:
                page.get_by_text("Add a question", exact=False).first.click()
                page.wait_for_timeout(500)
            quiz_item = page.locator(".quiz-item").nth(qi)
            # 題幹
            quiz_item.locator(".js-question-box .js-item-input").first.fill(item["question"])
            answers = item.get("answers", [])
            # 預設有 2 個答案框,不足就按「Add more answers」補到夠
            ans_inputs = quiz_item.locator(".answer-box .js-item-input")
            while ans_inputs.count() < len(answers):
                quiz_item.get_by_text("Add more answers", exact=False).first.click()
                page.wait_for_timeout(300)
            for ai, ans in enumerate(answers):
                ans_inputs.nth(ai).fill(str(ans))
            # 標正解(correct 是 0 起算的索引)
            correct = int(item.get("correct", 0))
            quiz_item.locator(".js-question-check").nth(correct).click()
    else:
        raise NotImplementedError(
            f"範本 {template} 的內容填寫尚未實作(目前已實測支援 quiz;"
            f"其他範本請先用 inspect 取得該編輯頁 DOM 再比照 quiz 補上)。")


def _save_and_get_url(page) -> str:
    """按下 Done 完成建立,回傳新活動的網址(已實測:button.js-done-button)。"""
    page.locator("button.js-done-button").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2500)
    return page.url


# ======================================================================
# 指令:assign —— TODO(需實測)
# ======================================================================
def cmd_assign(args):
    """把一個活動設成學生作業,取得分享連結。"""
    sync_playwright = _need_playwright()
    with sync_playwright() as p:
        browser, ctx = _context(p, headless=args.headless)
        page = ctx.new_page()
        if not _verify_logged_in(page):
            browser.close()
            die("登入已失效,請先重新 login。", code=2)
        try:
            page.goto(args.activity_url, wait_until="networkidle")
            # ---- TODO(需實測):Share → Set Assignment → 取得連結 ----
            raise NotImplementedError(
                "assign 流程選擇器尚未校正 —— 請先跑 "
                f"`inspect --url {args.activity_url}` 取得 Share 按鈕的 DOM。")
        except Exception as e:  # noqa
            _dump_debug(page, "assign_fail")
            die(f"設定作業失敗(選擇器待校正)。原始錯誤:{e}", code=3)
        finally:
            browser.close()


# ======================================================================
# 指令:results —— TODO(需實測)
# ======================================================================
def cmd_results(args):
    """抓取某活動的學生作答結果(My Results)。
    注意:這會碰到學生個資,請確認符合校方規範與 Wordwall 使用條款。"""
    sync_playwright = _need_playwright()
    with sync_playwright() as p:
        browser, ctx = _context(p, headless=args.headless)
        page = ctx.new_page()
        if not _verify_logged_in(page):
            browser.close()
            die("登入已失效,請先重新 login。", code=2)
        try:
            page.goto(f"{BASE}/myresults", wait_until="networkidle")
            # ---- TODO(需實測):選活動 → 讀 Results by Student 表格 ----
            raise NotImplementedError(
                "results 讀取選擇器尚未校正 —— 請先跑 "
                f"`inspect --url {BASE}/myresults`。")
        except Exception as e:  # noqa
            _dump_debug(page, "results_fail")
            die(f"讀取結果失敗(選擇器待校正)。原始錯誤:{e}", code=3)
        finally:
            browser.close()


# ======================================================================
# 參數解析
# ======================================================================
def build_parser():
    parser = argparse.ArgumentParser(
        prog="wordwall.py",
        description="用 CLI 控制 Wordwall(給 Claude Code 搭配 SKILL.md 使用)。")
    sub = parser.add_subparsers(dest="command", required=True)

    p_login = sub.add_parser("login", help="開瀏覽器手動登入並存下 session")
    p_login.set_defaults(func=cmd_login)

    p_grab = sub.add_parser("grab-session",
                            help="從你已登入的真實 Chrome 複製 Wordwall session(繞過 Google 封鎖)")
    p_grab.add_argument("--cdp-url", default="http://localhost:9222",
                        help="Chrome 除錯埠網址(預設 http://localhost:9222)")
    p_grab.set_defaults(func=cmd_grab_session)

    p_check = sub.add_parser("check", help="檢查登入是否還有效")
    p_check.set_defaults(func=cmd_check)

    p_tpl = sub.add_parser("templates", help="列出支援的範本代號")
    p_tpl.set_defaults(func=cmd_templates)

    p_ins = sub.add_parser("inspect", help="登入後 dump 指定頁面的 DOM(用來校正選擇器)")
    p_ins.add_argument("--url", required=True, help="要檢視的網址")
    p_ins.add_argument("--headless", action="store_true", help="不開視窗(預設開視窗方便觀察)")
    p_ins.set_defaults(func=cmd_inspect)

    p_new = sub.add_parser("create", help="依內容 JSON 建立活動〔選擇器待實測〕")
    p_new.add_argument("--content", required=True, help="內容 JSON 檔路徑(見 examples/)")
    p_new.add_argument("--template", help="範本代號(若 JSON 未指定)")
    p_new.add_argument("--headless", action="store_true")
    p_new.set_defaults(func=cmd_create)

    p_asg = sub.add_parser("assign", help="把活動設成學生作業〔選擇器待實測〕")
    p_asg.add_argument("--activity-url", required=True, help="活動網址")
    p_asg.add_argument("--headless", action="store_true")
    p_asg.set_defaults(func=cmd_assign)

    p_res = sub.add_parser("results", help="抓活動的學生作答結果〔選擇器待實測〕")
    p_res.add_argument("--headless", action="store_true")
    p_res.set_defaults(func=cmd_results)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
