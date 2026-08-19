#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wordwall CLI —— 讓 Codex、Claude Code 等 Agent 控制 Wordwall。

設計理念:這是一支「CLI 工具」,不是 MCP server。
Agent 透過終端機呼叫它,搭配同資料夾的 SKILL.md 就知道何時、怎麼用。
好處:不佔 context、無常駐 server、改壞了只要改這一支腳本(詳見 README.md)。

分工:
  ● 已可運作:login / grab-session / check / templates / inspect
  ● 已實測:文字與圖片 Quiz、正式作業連結、結果清單與 Excel 下載
  ● 選用:PDF 整頁／區域截圖；缺少元件時提供安裝指令
    指令失敗時會把截圖與 DOM 存到 debug/ 供校正,不會靜默失敗。

安全:本腳本「絕不」處理你的帳號密碼。login 指令會開一個瀏覽器視窗,
      由你「自己手動登入」(可用 Google 或 Email),再把登入後的 session 存下來重複使用。
"""

import argparse
import importlib.util
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from question_planner import build_question_plan, validate_asset_manifest
from wordwall_catalog import TEMPLATE_CATALOG, recommend_templates

# ---- 路徑設定 ----
CONFIG_DIR = Path.home() / ".wordwall"
STATE_FILE = CONFIG_DIR / "state.json"          # 登入後的 session(cookies 等)
CHROME_LOGIN_FILE = CONFIG_DIR / "chrome-login.json"
CHROME_LOGIN_PROFILE = CONFIG_DIR / "chrome-login-profile"
DEFAULT_CDP_PORT = 9333
DEBUG_DIR = Path(__file__).resolve().parent / "debug"
BASE = "https://wordwall.net"

# ---- Wordwall 範本能力目錄（內容模型與實作狀態見 wordwall_catalog.py） ----
TEMPLATES = {key: info["description"]
             for key, info in TEMPLATE_CATALOG.items()}
TEMPLATE_IDS = {key: info["id"] for key, info in TEMPLATE_CATALOG.items()}
QUIZ_TEMPLATES = {key for key, info in TEMPLATE_CATALOG.items()
                  if info["schema"] == "quiz" and info["implemented"]}
PAIR_TEMPLATES = {key for key, info in TEMPLATE_CATALOG.items()
                  if info["schema"] == "pair" and info["implemented"]}


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
            "    python -m pip install -r requirements.txt\n"
            "    python -m playwright install chromium\n"
            "或在 Windows PowerShell 執行: .\\setup.ps1")


def _interactive_login_help() -> str:
    """回傳 login 無法互動時的安全替代流程。"""
    return (
        "login 必須在可互動的 PowerShell 執行，因為登入後需要按 Enter。\n"
        "若由 Codex 或其他非互動終端操作，請改用:\n"
        "    python wordwall.py chrome-login\n"
        "    # 在開啟的真實 Chrome 由本人登入 Wordwall\n"
        "    python wordwall.py grab-session"
    )


def _find_chrome(chrome_path: str | None = None) -> Path:
    """尋找 Chrome 執行檔；明確指定時不做猜測。"""
    if chrome_path:
        candidate = Path(chrome_path).expanduser().resolve()
        if candidate.is_file():
            return candidate
        die(f"找不到指定的 Chrome: {candidate}", code=4)
    for name in ("chrome.exe", "chrome", "google-chrome", "google-chrome-stable"):
        found = shutil.which(name)
        if found:
            return Path(found).resolve()
    candidates = []
    if sys.platform == "win32":
        for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            root = os.environ.get(variable)
            if root:
                candidates.append(Path(root) / "Google" / "Chrome" / "Application" / "chrome.exe")
    elif sys.platform == "darwin":
        candidates.append(Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"))
    else:
        candidates.extend((Path("/usr/bin/google-chrome"), Path("/usr/bin/google-chrome-stable")))
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    die("找不到 Google Chrome。請安裝 Chrome，或用 --chrome-path 指定執行檔。", code=4)


def _port_is_available(port: int) -> bool:
    """確認本機除錯埠尚未被其他工具占用。"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False


def _resolve_grab_session_cdp_url(explicit_url: str | None) -> str:
    """只連使用者明確指定或本工具自己啟動並記錄的 Chrome。"""
    if explicit_url:
        return explicit_url.rstrip("/")
    if not CHROME_LOGIN_FILE.is_file():
        die("找不到本工具啟動的 Chrome 紀錄。請先執行:\n"
            "    python wordwall.py chrome-login\n"
            "本人登入完成後，再執行 python wordwall.py grab-session。", code=4)
    try:
        metadata = json.loads(CHROME_LOGIN_FILE.read_text(encoding="utf-8"))
        port = int(metadata["port"])
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        die(f"Chrome 登入紀錄已損壞: {CHROME_LOGIN_FILE}\n"
            "請重新執行 python wordwall.py chrome-login。", code=4)
    if port < 1 or port > 65535:
        die(f"Chrome 登入紀錄中的埠號無效: {port}\n"
            "請重新執行 python wordwall.py chrome-login。", code=4)
    try:
        profile = Path(metadata["profile_dir"]).expanduser().resolve()
        active_port_file = profile / "DevToolsActivePort"
        active_port = int(active_port_file.read_text(
            encoding="utf-8").splitlines()[0])
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        die("找不到本工具專用 Chrome 的有效 DevToolsActivePort。\n"
            "請確認 Chrome 仍開著，或重新執行 python wordwall.py chrome-login。",
            code=4)
    if active_port != port:
        die("Chrome 登入紀錄與專用 profile 的實際埠不一致。為避免抓到其他工具的 "
            "session，本工具拒絕連線。\n"
            "請重新執行 python wordwall.py chrome-login。", code=4)
    return f"http://127.0.0.1:{port}"


def _missing_pdf_packages() -> list[str]:
    """回傳 PDF 截圖功能缺少的 pip 套件名稱。"""
    checks = (("pypdfium2", "pypdfium2"), ("PIL", "Pillow"))
    return [package for module, package in checks
            if importlib.util.find_spec(module) is None]


def _need_pdf_tools():
    """延遲載入 PDF 截圖套件，缺少時提供可直接執行的安裝指令。"""
    missing = _missing_pdf_packages()
    if missing:
        die("尚未安裝 PDF 截圖選用元件: " + ", ".join(missing) + "\n"
            "請執行:\n"
            "    python -m pip install -r requirements-pdf.txt\n"
            "或在 Windows PowerShell 執行: .\\setup.ps1 -WithPdf")
    import pypdfium2 as pdfium
    from PIL import ImageOps
    return pdfium, ImageOps


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


def _resolve_image_path(value: str, base_dir: Path) -> Path:
    """將 JSON 內的圖片路徑解析為絕對路徑並確認可讀。"""
    image_path = Path(value).expanduser()
    if not image_path.is_absolute():
        image_path = base_dir / image_path
    image_path = image_path.resolve()
    if not image_path.is_file():
        raise ValueError(f"找不到題目圖片:{image_path}")
    return image_path


def _normalize_media(value, base_dir: Path, fallback_image=None,
                     field_name: str = "內容") -> dict:
    """把字串或 {text,image} 正規化成共用媒體物件。"""
    if isinstance(value, dict):
        text_value = value.get("text", "")
        image_value = value.get("image") or value.get("image_path")
    else:
        text_value = value if value is not None else ""
        image_value = None
    image_value = image_value or fallback_image
    text_value = str(text_value).strip()
    image_path = (_resolve_image_path(str(image_value), base_dir)
                  if image_value else None)
    if not text_value and image_path is None:
        raise ValueError(f"{field_name} 必須至少包含文字或圖片。")
    return {"text": text_value, "image": image_path}


def _prepare_quiz_content(content: dict, base_dir: Path) -> dict:
    """驗證並正規化 Quiz 家族的題幹、答案及圖片。"""
    items = content.get("items", [])
    if not items:
        raise ValueError("quiz 內容沒有任何題目(items 為空)。")
    prepared = []
    for number, item in enumerate(items, start=1):
        answers = item.get("answers", [])
        if not 2 <= len(answers) <= 6:
            raise ValueError(f"第 {number} 題答案數必須介於 2 到 6 個。")
        correct = int(item.get("correct", 0))
        if correct < 0 or correct >= len(answers):
            raise ValueError(f"第 {number} 題 correct 超出答案範圍。")
        question = _normalize_media(
            item.get("question", ""), base_dir,
            item.get("image") or item.get("image_path"),
            f"第 {number} 題題幹")
        prepared_answers = [
            _normalize_media(answer, base_dir, field_name=
                             f"第 {number} 題第 {index} 個答案")
            for index, answer in enumerate(answers, start=1)
        ]
        prepared.append({"question": question,
                         "answers": prepared_answers,
                         "correct": correct})
    return {"schema": "quiz", "items": prepared}


def _prepare_pair_content(content: dict, base_dir: Path) -> dict:
    """驗證並正規化左右兩端都可放文字／圖片的配對內容。"""
    pairs = content.get("pairs") or content.get("items") or []
    if not pairs:
        raise ValueError("pair 內容沒有任何配對(pairs 為空)。")
    prepared = []
    for number, pair in enumerate(pairs, start=1):
        left_value = pair.get("left", pair.get("keyword", ""))
        right_value = pair.get("right", pair.get("definition", ""))
        left = _normalize_media(
            left_value, base_dir,
            pair.get("left_image") or pair.get("keyword_image"),
            f"第 {number} 組左端")
        right = _normalize_media(
            right_value, base_dir,
            pair.get("right_image") or pair.get("definition_image"),
            f"第 {number} 組右端")
        prepared.append({"left": left, "right": right})
    return {"schema": "pair", "items": prepared}


def _prepare_group_content(content: dict, base_dir: Path) -> dict:
    """驗證分組名稱與每組項目；兩層都可使用文字／圖片。"""
    groups = content.get("groups") or []
    if not groups:
        raise ValueError("group 內容沒有任何群組(groups 為空)。")
    prepared_groups = []
    for group_number, group in enumerate(groups, start=1):
        title_value = group.get(
            "title", group.get("name", group.get("group", "")))
        title = _normalize_media(
            title_value, base_dir,
            group.get("image") or group.get("image_path"),
            f"第 {group_number} 組名稱")
        values = group.get("items") or []
        if not 1 <= len(values) <= 20:
            raise ValueError(
                f"第 {group_number} 組項目數必須介於 1 到 20 個。")
        items = [
            _normalize_media(value, base_dir, field_name=
                             f"第 {group_number} 組第 {index} 個項目")
            for index, value in enumerate(values, start=1)
        ]
        prepared_groups.append({"title": title, "items": items})
    return {"schema": "group", "groups": prepared_groups}


def _prepare_true_false_content(content: dict, base_dir: Path) -> dict:
    """將是非敘述拆成 Wordwall 固定的真／假兩組。"""
    values = content.get("items") or content.get("statements") or []
    if not values:
        raise ValueError("true_or_false 沒有任何敘述(items 為空)。")
    groups = [
        {"title": {"text": "真", "image": None}, "items": []},
        {"title": {"text": "假", "image": None}, "items": []},
    ]
    for number, value in enumerate(values, start=1):
        if not isinstance(value, dict) or "correct" not in value:
            raise ValueError(
                f"第 {number} 題必須是包含 statement 與 correct 的物件。")
        statement = value.get("statement", value.get("text", ""))
        media = _normalize_media(
            statement, base_dir,
            value.get("image") or value.get("image_path"),
            f"第 {number} 題敘述")
        correct = value["correct"]
        if not isinstance(correct, bool):
            raise ValueError(f"第 {number} 題 correct 必須是 true 或 false。")
        groups[0 if correct else 1]["items"].append(media)
    if any(not group["items"] for group in groups):
        raise ValueError("true_or_false 必須至少各有一題 true 與 false。")
    return {"schema": "fixed_group", "groups": groups}


def _prepare_single_content(content: dict, base_dir: Path) -> dict:
    """驗證轉盤、隨機卡等單項清單。"""
    values = content.get("items") or content.get("entries") or []
    if not values:
        raise ValueError("single 內容沒有任何項目(items 為空)。")
    items = [
        _normalize_media(value, base_dir, field_name=f"第 {index} 個項目")
        for index, value in enumerate(values, start=1)
    ]
    return {"schema": "single", "items": items}


def _parse_cloze_sentence(value: str, item_number: int) -> tuple[str, list[dict]]:
    """把「文字 {{答案}} 文字」轉成可見句子與插入位置。"""
    source = str(value).strip()
    matches = list(re.finditer(r"\{\{\s*(.+?)\s*\}\}", source))
    if not matches:
        raise ValueError(
            f"第 {item_number} 頁 sentence 至少要有一個 {{{{答案}}}} 標記。")
    if len(matches) > 1:
        raise ValueError(
            f"第 {item_number} 頁目前只支援一個 {{{{答案}}}} 標記；"
            "請拆成多頁。")
    visible_parts = []
    gaps = []
    cursor = 0
    visible_length = 0
    for match in matches:
        prefix = source[cursor:match.start()]
        visible_parts.append(prefix)
        visible_length += len(prefix)
        answer = match.group(1).strip()
        if not answer:
            raise ValueError(f"第 {item_number} 頁有空白的缺字答案。")
        gaps.append({"position": visible_length, "answer": answer})
        visible_parts.append(answer)
        visible_length += len(answer)
        cursor = match.end()
    visible_parts.append(source[cursor:])
    visible = "".join(visible_parts)
    if not visible:
        raise ValueError(f"第 {item_number} 頁缺少可見句子。")
    return visible, gaps


def _prepare_cloze_content(content: dict, base_dir: Path) -> dict:
    """驗證 Complete the sentence 的頁面、缺字與錯誤選項。"""
    pages = content.get("pages") or content.get("items") or []
    if not pages:
        raise ValueError("clue 內容沒有任何頁面(pages 為空)。")
    prepared = []
    for number, page in enumerate(pages, start=1):
        if not isinstance(page, dict):
            raise ValueError(f"第 {number} 頁必須是包含 sentence 的物件。")
        visible, gaps = _parse_cloze_sentence(page.get("sentence", ""), number)
        prompt = _normalize_media(
            visible, base_dir, page.get("image") or page.get("image_path"),
            f"第 {number} 頁句子")
        wrong_answers = [
            str(value).strip()
            for value in (page.get("wrong_answers")
                          or page.get("distractors") or [])
        ]
        if any(not value for value in wrong_answers):
            raise ValueError(f"第 {number} 頁錯誤選項不可為空白。")
        prepared.append({
            "prompt": prompt,
            "gaps": gaps,
            "wrong_answers": wrong_answers,
        })
    return {"schema": "cloze", "items": prepared}


def _prepare_diagram_content(content: dict, base_dir: Path) -> dict:
    """驗證 Labelled diagram 的底圖、標籤與 0..1 正規化座標。"""
    image_value = content.get("image") or content.get("image_path")
    if not image_value:
        raise ValueError("labelled_diagram 必須指定底圖 image。")
    diagram = {
        "text": "底圖",
        "image": _resolve_image_path(str(image_value), base_dir),
    }
    values = content.get("labels") or content.get("items") or []
    if not values:
        raise ValueError("labelled_diagram 沒有任何標籤(labels 為空)。")
    labels = []
    for number, value in enumerate(values, start=1):
        if not isinstance(value, dict):
            raise ValueError(f"第 {number} 個標籤必須包含 text、x、y。")
        label_value = value.get("label", value.get("text", ""))
        media = _normalize_media(
            label_value, base_dir,
            value.get("image") or value.get("image_path"),
            f"第 {number} 個標籤")
        try:
            x = float(value["x"])
            y = float(value["y"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(
                f"第 {number} 個標籤 x、y 必須是 0 到 1 的數字。") from error
        if not 0 <= x <= 1 or not 0 <= y <= 1:
            raise ValueError(f"第 {number} 個標籤 x、y 必須介於 0 到 1。")
        labels.append({"label": media, "x": x, "y": y})
    return {"schema": "diagram", "diagram": diagram, "items": labels}


def _count_media_images(value) -> int:
    """遞迴計算 prepared 結構中的共用媒體物件圖片數。"""
    if isinstance(value, dict):
        if "text" in value and "image" in value:
            return int(value["image"] is not None)
        return sum(_count_media_images(child) for child in value.values())
    if isinstance(value, list):
        return sum(_count_media_images(child) for child in value)
    return 0


def _prepare_content(content: dict, base_dir: Path, template: str) -> dict:
    """依範本內容模型驗證，並產生建立器共用資料。"""
    info = TEMPLATE_CATALOG[template]
    if not info["implemented"]:
        raise NotImplementedError(
            f"範本 {template} 已完成能力分類，但建立器尚未實作。"
            "請先用 recommend 查詢已可建立的相容範本。")
    if template == "true_or_false":
        prepared = _prepare_true_false_content(content, base_dir)
    elif template == "matching_pairs":
        mode = str(content.get("mode", "same")).casefold()
        if mode in ("same", "simple", "mode1"):
            prepared = _prepare_single_content(content, base_dir)
            prepared["editor_mode"] = 1
        elif mode in ("different", "pair", "mode2"):
            prepared = _prepare_pair_content(content, base_dir)
            prepared["editor_mode"] = 2
        else:
            raise ValueError(
                "matching_pairs mode 必須是 same 或 different。")
    elif info["schema"] == "quiz":
        prepared = _prepare_quiz_content(content, base_dir)
    elif info["schema"] == "pair":
        prepared = _prepare_pair_content(content, base_dir)
    elif info["schema"] == "group":
        prepared = _prepare_group_content(content, base_dir)
    elif info["schema"] in ("single", "single_mode"):
        mode = str(content.get("mode", "simple")).casefold()
        if info["schema"] == "single_mode" and mode not in ("simple", "mode1"):
            raise ValueError(
                f"{template} 目前只支援簡易模式(mode=simple)。")
        prepared = _prepare_single_content(content, base_dir)
    elif template == "complete_the_sentence":
        prepared = _prepare_cloze_content(content, base_dir)
    elif info["schema"] == "diagram":
        prepared = _prepare_diagram_content(content, base_dir)
    else:
        raise NotImplementedError(f"尚未實作內容模型: {info['schema']}")
    if prepared["schema"] in ("group", "fixed_group"):
        count = len(prepared["groups"])
        prepared["group_count"] = count
        prepared["item_count"] = sum(
            len(group["items"]) for group in prepared["groups"])
        if prepared["schema"] == "fixed_group":
            count = prepared["item_count"]
            count_label = "題目數"
        else:
            count_label = "群組數"
    else:
        count = len(prepared["items"])
        prepared["item_count"] = count
        count_label = "項目數"
    if count < info["min"] or count > info["max"]:
        raise ValueError(
            f"{template} {count_label}必須介於 {info['min']} 到 {info['max']}，目前為 {count}。")
    prepared["template"] = template
    prepared["image_count"] = _count_media_images(prepared)
    return prepared


def _validate_quiz_content(content: dict, base_dir: Path) -> list[Path | None]:
    """向下相容：驗證 Quiz 並回傳每題題幹圖片路徑。"""
    prepared = _prepare_quiz_content(content, base_dir)
    return [item["question"]["image"] for item in prepared["items"]]


def _set_checkbox(page, selector: str, enabled: bool):
    """只在狀態不同時切換 checkbox。"""
    checkbox = page.locator(selector)
    checkbox.wait_for(state="attached", timeout=10000)
    if checkbox.is_checked() != enabled:
        checkbox.click()


def _deadline_for_wordwall(value: str) -> str:
    """將 YYYY-MM-DD 轉為 Wordwall 日期欄使用的 DD/MM/YYYY。"""
    return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")


# ======================================================================
# 指令:login —— 已可運作
# ======================================================================
def cmd_login(args):
    """開瀏覽器讓「使用者本人」手動登入,再把 session 存起來重複使用。"""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        die(_interactive_login_help(), code=2)
    sync_playwright = _need_playwright()
    CONFIG_DIR.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 一定要有頭,讓你看得到登入畫面
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(f"{BASE}/", wait_until="domcontentloaded")
        print("=" * 60)
        print("請在剛開啟的瀏覽器視窗『手動登入』Wordwall。")
        print("[注意] 請用『Email + 密碼』登入,不要點『Sign in with Google』——")
        print("   Google 會封鎖自動化瀏覽器的登入。若你的帳號只有 Google,")
        print("   請先在登入頁用『Forgot password』設一組密碼,或改用 grab-session。")
        print("(本程式不會、也看不到你的密碼)")
        print("登入完成、看到你的活動清單後,回到這個終端機按 Enter……")
        print("=" * 60)
        try:
            input()
        except EOFError:
            browser.close()
            die(_interactive_login_help(), code=2)
        ctx.storage_state(path=str(STATE_FILE))
        print(f"[完成] 已把登入狀態存到:{STATE_FILE}")
        print("之後其他指令會自動沿用這個登入,不必再登。過期了再跑一次 login 即可。")
        browser.close()


# ======================================================================
# 指令:chrome-login / grab-session —— 使用真實 Chrome 安全登入
# ======================================================================
def cmd_chrome_login(args):
    """啟動本工具專用的真實 Chrome，由使用者本人登入 Wordwall。"""
    if args.port < 1 or args.port > 65535:
        die("--port 必須介於 1 到 65535。", code=4)
    if not _port_is_available(args.port):
        next_port = args.port + 1 if args.port < 65535 else DEFAULT_CDP_PORT
        die(f"連接埠 {args.port} 已被其他程式占用，為避免抓到別的 Chrome session，"
            "本工具不會連線。\n"
            f"請改用: python wordwall.py chrome-login --port {next_port}", code=4)
    chrome_path = _find_chrome(args.chrome_path)
    profile = Path(args.profile_dir).expanduser().resolve()
    profile.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    command = [str(chrome_path), f"--remote-debugging-port={args.port}",
               f"--user-data-dir={profile}", "--no-first-run", "--new-window",
               f"{BASE}/account/login"]
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    try:
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL,
                                   creationflags=creationflags)
    except OSError as error:
        die(f"無法啟動 Chrome: {error}", code=4)
    metadata = {"port": args.port, "profile_dir": str(profile),
                "chrome_path": str(chrome_path), "pid": process.pid,
                "created_at": datetime.now().isoformat(timespec="seconds")}
    CHROME_LOGIN_FILE.write_text(json.dumps(metadata, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
    print(f"[完成] 已開啟 Wordwall 專用 Chrome（埠 {args.port}）。")
    print(f"專用個人資料夾: {profile}")
    print("請由本人在該視窗登入 Wordwall；看到活動清單後執行:")
    print("    python wordwall.py grab-session")


def cmd_grab_session(args):
    """從『你已登入的真實 Chrome』複製 Wordwall 登入狀態,存成本工具的 session。

    這條路不自動化登入,所以 Google 不會擋。步驟:
      1. 執行:python wordwall.py chrome-login
      2. 在專用 Chrome 裡登入 wordwall.net(可用 Google 或 Email)。
      3. 執行:python wordwall.py grab-session
    """
    cdp_url = _resolve_grab_session_cdp_url(args.cdp_url)
    sync_playwright = _need_playwright()
    CONFIG_DIR.mkdir(exist_ok=True)
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(cdp_url)
        except Exception as e:  # noqa
            die(f"連不上 Wordwall 專用 Chrome({cdp_url})。\n"
                "     請重新執行 python wordwall.py chrome-login，登入後再試。\n"
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
# 指令:doctor —— 首次安裝與選用功能診斷
# ======================================================================
def cmd_doctor(args):
    """檢查 Python、Playwright、Chromium、登入與 PDF 選用元件。"""
    issues = []
    version = ".".join(str(value) for value in sys.version_info[:3])
    python_ok = sys.version_info >= (3, 10)
    print(f"[{'OK' if python_ok else '缺少'}] Python {version}: {sys.executable}")
    if not python_ok:
        issues.append("請安裝 Python 3.10 以上: https://www.python.org/downloads/")

    playwright_ok = importlib.util.find_spec("playwright") is not None
    print(f"[{'OK' if playwright_ok else '缺少'}] Playwright Python 套件")
    if not playwright_ok:
        issues.append("python -m pip install -r requirements.txt")

    browser_ok = False
    if playwright_ok and not args.skip_browser:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                browser.close()
            browser_ok = True
            print("[OK] Playwright Chromium 可啟動")
        except Exception:
            print("[缺少] Playwright Chromium 無法啟動")
            issues.append("python -m playwright install chromium")
    elif args.skip_browser:
        print("[略過] Chromium 啟動檢查")

    if STATE_FILE.exists():
        print(f"[OK] 已找到本機登入狀態: {STATE_FILE}")
    else:
        print("[尚未登入] 找不到本機登入狀態")
        print("  下一步: python wordwall.py login")

    if args.login:
        if not STATE_FILE.exists() or not browser_ok:
            issues.append("完成核心安裝後執行: python wordwall.py login")
        else:
            try:
                sync_playwright = _need_playwright()
                with sync_playwright() as p:
                    browser, ctx = _context(p, headless=True)
                    page = ctx.new_page()
                    logged_in = _verify_logged_in(page)
                    browser.close()
                print(f"[{'OK' if logged_in else '失效'}] Wordwall 登入狀態")
                if not logged_in:
                    issues.append("python wordwall.py login")
            except Exception:
                print("[失敗] 無法驗證 Wordwall 登入狀態")
                issues.append("python wordwall.py login")

    if args.pdf:
        missing_pdf = _missing_pdf_packages()
        if missing_pdf:
            print("[缺少] PDF 截圖元件: " + ", ".join(missing_pdf))
            issues.append("python -m pip install -r requirements-pdf.txt")
        else:
            print("[OK] PDF 截圖元件 pypdfium2 + Pillow")

    if issues:
        print("\n建議依序執行:")
        for command in dict.fromkeys(issues):
            print(f"  {command}")
        raise SystemExit(1)
    print("\n[OK] 所選檢查全部通過。")


def _parse_crop_box(value: str | None) -> tuple[float, float, float, float] | None:
    """解析 PDF 點座標 x0,y0,x1,y1。"""
    if value is None:
        return None
    try:
        box = tuple(float(part.strip()) for part in value.split(","))
    except ValueError as error:
        raise ValueError("--crop 必須是 x0,y0,x1,y1 四個數字。") from error
    if len(box) != 4 or box[0] < 0 or box[1] < 0 or box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError("--crop 必須是有效的 x0,y0,x1,y1 PDF 點座標。")
    return box


def cmd_pdf_screenshot(args):
    """將 PDF 指定頁渲染為 PNG，可選擇以 PDF 點座標裁切。"""
    pdfium, ImageOps = _need_pdf_tools()
    if args.scale <= 0:
        die("--scale 必須大於 0。")
    if args.padding < 0:
        die("--padding 不可小於 0。")
    source = Path(args.input).expanduser().resolve()
    if not source.is_file():
        die(f"找不到 PDF: {source}")
    if source.suffix.lower() != ".pdf":
        die("--input 必須是 PDF 檔。")
    try:
        crop = _parse_crop_box(args.crop)
    except ValueError as error:
        die(str(error))

    pdf = pdfium.PdfDocument(str(source))
    page_index = args.page - 1
    if page_index < 0 or page_index >= len(pdf):
        die(f"--page 超出範圍；此 PDF 共 {len(pdf)} 頁。")
    page = pdf[page_index]
    image = page.render(scale=args.scale).to_pil().convert("RGB")
    if crop:
        width, height = page.get_size()
        if crop[2] > width or crop[3] > height:
            die(f"--crop 超出頁面範圍；頁面大小為 {width:.1f} x {height:.1f} 點。")
        image = image.crop(tuple(round(value * args.scale) for value in crop))
    if args.padding:
        image = ImageOps.expand(image, border=args.padding, fill="white")

    output = Path(args.output).expanduser().resolve()
    if output.suffix.lower() != ".png":
        output = output / f"{source.stem}_page_{args.page}.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, optimize=True)
    print(json.dumps({
        "status": "created",
        "input": str(source),
        "page": args.page,
        "crop": crop,
        "size": list(image.size),
        "output": str(output),
    }, ensure_ascii=False, indent=2))


# ======================================================================
# 指令:templates —— 已可運作
# ======================================================================
def cmd_templates(args):
    """列出 Wordwall 範本的 schema、媒體能力與建立器狀態。"""
    rows = [{"template": key, **info}
            for key, info in TEMPLATE_CATALOG.items()]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    print("範本代號 / schema / 媒體能力 / CLI 建立器:\n")
    for row in rows:
        status = "可建立" if row["implemented"] else "待開發"
        media = ",".join(row["media"])
        print(f"  {row['template']:<24} {row['schema']:<12} "
              f"{media:<29} {status}  {row['description']}")


def cmd_recommend(args):
    """依使用者意圖、內容模型與媒體組合推薦相容範本。"""
    rows = recommend_templates(
        schema=args.schema, media=args.media, intent=args.intent,
        implemented_only=args.implemented_only)
    if not rows:
        die("找不到符合條件的範本；可移除部分條件或先執行 templates。")
    print(json.dumps(rows, ensure_ascii=False, indent=2))


def cmd_plan(args):
    """自然語言選型、三級素材決策，以及選用內容 JSON 預檢。"""
    try:
        plan = build_question_plan(
            args.request, requested_level=args.level,
            requested_template=args.template)
        if args.content:
            content_path = Path(args.content).expanduser().resolve()
            content = json.loads(content_path.read_text(encoding="utf-8"))
            template = (args.template or content.get("template")
                        or plan["decision"]["template"])
            if template not in TEMPLATE_CATALOG:
                raise ValueError(f"未知範本: {template}")
            prepared = _prepare_content(content, content_path.parent, template)
            plan["content_preflight"] = {
                "status": "dry-run-ok",
                "content": str(content_path),
                "template": template,
                "schema": prepared["schema"],
                "item_count": prepared["item_count"],
                "image_count": prepared["image_count"],
            }
            plan["next_commands"] = [
                f'python wordwall.py create --content "{content_path}" --dry-run',
                f'python wordwall.py create --content "{content_path}" --editor-check --headless',
                "等待使用者確認後，才移除 --editor-check 正式建立。",
            ]
        else:
            plan["content_preflight"] = {
                "status": "awaiting-content-json",
                "instruction": "依 content_contract 產生 JSON 後重新執行 plan --content。",
            }
            plan["next_commands"] = [
                "依 content_contract 產生內容 JSON 與定稿素材。",
                "重新執行 plan 並加上 --content <JSON>。",
                "通過後執行 create --editor-check；等待使用者確認。",
            ]
        if args.assets:
            assets_path = Path(args.assets).expanduser().resolve()
            manifest = json.loads(assets_path.read_text(encoding="utf-8"))
            plan["asset_preflight"] = validate_asset_manifest(
                manifest, assets_path.parent, plan)
            plan["asset_preflight"]["manifest"] = str(assets_path)
        else:
            plan["asset_preflight"] = {
                "status": "awaiting-asset-manifest"
                if plan["decision"]["asset_level"] != "text"
                else "not-required",
            }
    except (OSError, json.JSONDecodeError, ValueError,
            NotImplementedError) as error:
        die(str(error))

    output_text = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        plan["plan_file"] = str(output)
        output_text = json.dumps(plan, ensure_ascii=False, indent=2)
        output.write_text(output_text + "\n", encoding="utf-8")
    print(output_text)


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
# 指令:create —— 建立文字或圖片 Quiz
# ======================================================================
def cmd_create(args):
    """依內容 JSON 建立一個 Wordwall 活動。

    內容 JSON 範例見 examples/。基本結構:
        { "template": "quiz", "title": "...", "items": [...] }
    """
    content_path = Path(args.content).expanduser().resolve()
    content = json.loads(content_path.read_text(encoding="utf-8"))
    template = args.template or content.get("template")
    if not template:
        die("內容 JSON 未指定 template,也沒給 --template。")
    if template not in TEMPLATES:
        die(f"未知範本:{template}(用 `templates` 指令查可用清單)")
    content["template"] = template
    try:
        prepared = _prepare_content(content, content_path.parent, template)
    except (ValueError, NotImplementedError) as error:
        die(str(error))

    if args.dry_run:
        print(json.dumps({
            "status": "dry-run-ok",
            "template": template,
            "schema": prepared["schema"],
            "title": content.get("title", ""),
            "item_count": prepared["item_count"],
            "image_count": prepared["image_count"],
            "content": str(content_path),
        }, ensure_ascii=False, indent=2))
        return

    sync_playwright = _need_playwright()
    with sync_playwright() as p:
        browser, ctx = _context(p, headless=args.headless)
        page = ctx.new_page()
        if not _verify_logged_in(page):
            browser.close()
            die("登入已失效,請先重新 login。", code=2)
        try:
            page.goto(f"{BASE}/create", wait_until="networkidle")
            # 1) 選範本
            _click_template(page, template)
            # 2) 填標題與內容(不同範本欄位不同,見 _fill_content)
            _fill_content(page, content, prepared)
            if args.editor_check:
                print(json.dumps(
                    _verify_editor_content(page, prepared),
                    ensure_ascii=False, indent=2))
                return
            # 3) 儲存 / 建立,取得活動網址
            url = _save_and_get_url(page, content.get("title", ""))
            print(f"[完成] 已建立活動:{url}")
        except Exception as e:  # noqa
            _dump_debug(page, "create_fail")
            die(f"建立活動時選擇器對不上(很可能是 Wordwall 改版或尚未校正)。\n"
                f"     請用 `inspect --url {BASE}/create` 取得真實 DOM 再校正 _click_template / _fill_content。\n"
                f"     原始錯誤:{e}", code=3)
        finally:
            browser.close()


def _click_template(page, template: str):
    """在建立頁點選指定範本卡片。

    Wordwall 近期將卡片外層由 ``.template.js-item`` 改為
    ``.template-icon-v2.js-template-icon-v2.js-item``；保留舊選擇器並
    依序嘗試新版結構，避免依賴視覺位置或文字猜測。
    """
    tid = TEMPLATE_IDS.get(template)
    if tid is None:
        raise ValueError(f"沒有 {template} 的 template-id 對照,請先補進 TEMPLATE_IDS。")
    selectors = [
        f'.template.js-item[data-template-id="{tid}"]',
        f'.template-icon-v2.js-template-icon-v2.js-item[data-template-id="{tid}"]',
        f'[data-template-id="{tid}"].js-item',
    ]
    last_error = None
    for selector in selectors:
        card = page.locator(selector).first
        try:
            card.wait_for(state="visible", timeout=5000)
            card.click()
            page.wait_for_load_state("networkidle")
            return
        except Exception as exc:
            last_error = exc
    raise TimeoutError(
        f"找不到可見的 {template} 範本卡片 (template-id={tid})。"
    ) from last_error


def _upload_editor_image(page, container, image_path: Path | None):
    """在任一題幹／答案／配對端欄位上傳圖片。"""
    if image_path is None:
        return
    container.locator(".js-item-image-placeholder").click()
    upload_button = page.locator("#upload_image_button:visible")
    upload_button.wait_for(state="visible", timeout=10000)
    with page.expect_file_chooser(timeout=10000) as chooser_info:
        upload_button.click()
    chooser_info.value.set_files(str(image_path))
    page.locator(".js-modal-view-wrapper").wait_for(
        state="hidden", timeout=30000)
    container.locator(".js-item-image").wait_for(
        state="visible", timeout=30000)


def _ensure_editor_items(page, selector: str, count: int):
    """以語系無關的 DOM class 增加題目／配對列到指定數量。"""
    rows = page.locator(selector)
    while rows.count() < count:
        previous = rows.count()
        page.locator(".js-editor-add-item:visible").last.click()
        page.wait_for_function(
            "([selector, previous]) => document.querySelectorAll(selector).length > previous",
            arg=[selector, previous])
    return rows


def _fill_quiz_content(page, prepared: dict):
    """填寫共用 Quiz 編輯器家族。"""
    items = prepared["items"]
    rows = _ensure_editor_items(page, ".quiz-item", len(items))
    for qi, item in enumerate(items):
        quiz_item = rows.nth(qi)
        question_box = quiz_item.locator(".js-question-box").first
        question_box.locator(".js-item-input").first.fill(
            item["question"]["text"])
        _upload_editor_image(page, question_box, item["question"]["image"])

        answers = item["answers"]
        answer_boxes = quiz_item.locator(".answer-box")
        while answer_boxes.count() < len(answers):
            previous = answer_boxes.count()
            quiz_item.locator(".js-editor-add-answer").click()
            page.wait_for_function(
                "([index, previous]) => document.querySelectorAll('.quiz-item')[index].querySelectorAll('.answer-box').length > previous",
                arg=[qi, previous])
        for ai, answer in enumerate(answers):
            answer_box = answer_boxes.nth(ai)
            answer_box.locator(".js-item-input").fill(answer["text"])
            _upload_editor_image(page, answer_box, answer["image"])
        quiz_item.locator(".js-question-check").nth(item["correct"]).click()


def _fill_pair_content(page, prepared: dict):
    """填寫左右雙端的 Match／Flash cards／Balloon pop 家族。"""
    items = prepared["items"]
    rows = _ensure_editor_items(
        page, ".js-editor-child-items.double-item", len(items))
    for index, item in enumerate(items):
        row = rows.nth(index)
        cells = row.locator(".double-inner")
        if cells.count() < 2:
            raise RuntimeError(f"第 {index + 1} 組找不到左右兩個內容欄位。")
        for cell_index, side in enumerate(("left", "right")):
            cell = cells.nth(cell_index)
            cell.locator(".js-item-input").fill(item[side]["text"])
            _upload_editor_image(page, cell, item[side]["image"])


def _fill_group_content(page, prepared: dict, rename_titles: bool = True):
    """填寫 Group sort／Speed sorting 的群組與群組內項目。"""
    expected_groups = prepared["groups"]
    groups = page.locator("#editor_component_0 .js-group-component")
    while groups.count() < len(expected_groups):
        previous = groups.count()
        page.locator(
            ".editor-add-item.group.js-editor-add-item:visible").click()
        page.wait_for_function(
            "previous => document.querySelectorAll('#editor_component_0 .js-group-component').length > previous",
            arg=previous)
    for group_index, expected_group in enumerate(expected_groups):
        group = groups.nth(group_index)
        if rename_titles:
            edit_button = group.locator(".js-group-title .fa-pen-to-square")
            edit_button.click()
            rename_modal = page.locator(".js-modal-view-wrapper:visible")
            rename_modal.locator(".js-input-text").fill(
                expected_group["title"]["text"])
            rename_modal.locator(".js-ok-button").click()
            rename_modal.wait_for(state="hidden", timeout=10000)
            _upload_editor_image(
                page, group.locator(".group-header"),
                expected_group["title"]["image"])

        child_container = group.locator(
            ":scope > div > .js-editor-child-items").first
        rows = child_container.locator(":scope > .js-item")
        while rows.count() < len(expected_group["items"]):
            previous = rows.count()
            group.locator(".js-editor-add-item:visible").click()
            page.wait_for_function(
                "([groupIndex, previous]) => document.querySelectorAll('#editor_component_0 .js-group-component')[groupIndex].querySelectorAll(':scope > div > .js-editor-child-items > .js-item').length > previous",
                arg=[group_index, previous])
        for item_index, item in enumerate(expected_group["items"]):
            row = rows.nth(item_index)
            row.locator(".single-item .js-item-input").fill(item["text"])
            _upload_editor_image(page, row, item["image"])


def _fill_single_content(page, prepared: dict):
    """填寫簡易轉盤、隨機卡等單項清單。"""
    simple_mode = page.locator("#option_mode1")
    if simple_mode.count():
        simple_mode.check()
    selector = (
        "#editor_component_0 > .item-collection > "
        ".js-editor-child-items > .js-item")
    rows = _ensure_editor_items(page, selector, len(prepared["items"]))
    for index, item in enumerate(prepared["items"]):
        row = rows.nth(index)
        row.locator(".single-item .js-item-input").fill(item["text"])
        _upload_editor_image(page, row, item["image"])


def _add_cloze_word(page, row, selector: str, value: str):
    """透過 Wordwall 自己的對話框新增正解或錯誤選項。"""
    row.locator(selector).click()
    modal = page.locator(".js-modal-view-wrapper:visible")
    modal.locator(".js-input-text").fill(value)
    modal.locator(".js-ok-button").click()
    modal.wait_for(state="hidden", timeout=10000)


def _fill_cloze_content(page, prepared: dict):
    """填寫 Complete the sentence，並在指定位置插入缺字。"""
    selector = (
        "#editor_component_0 > .item-collection > .js-editor-child-items "
        "> .complete-the-sentence-editor-wrapper")
    rows = _ensure_editor_items(page, selector, len(prepared["items"]))
    for index, item in enumerate(prepared["items"]):
        row = rows.nth(index)
        editor = row.locator(".js-complete-the-sentence-editor")
        editor.fill(item["prompt"]["text"])
        _upload_editor_image(page, row, item["prompt"]["image"])
        for gap in item["gaps"]:
            editor.press("Home")
            for _ in range(gap["position"]):
                editor.press("ArrowRight")
            for _ in gap["answer"]:
                editor.press("Shift+ArrowRight")
            selected_button = row.locator(".js-add-selected-word:visible")
            selected_button.wait_for(state="visible", timeout=10000)
            if gap["answer"] not in selected_button.inner_text():
                raise RuntimeError(
                    f"缺字選取不符，預期標記：{gap['answer']}")
            selected_button.click()
        for wrong_answer in item["wrong_answers"]:
            _add_cloze_word(
                page, row, ".js-add-incorrect-word:visible", wrong_answer)


def _fill_diagram_content(page, prepared: dict):
    """上傳 Labelled diagram 底圖，填標籤並拖曳 pin 到正規化座標。"""
    holder = page.locator("#editor_component_0 .js-item-image-holder").first
    _upload_editor_image(page, holder, prepared["diagram"]["image"])

    row_selector = (
        "#editor_component_1 > .item-collection > "
        ".js-editor-child-items > .js-item")
    rows = page.locator(row_selector)
    while rows.count() < len(prepared["items"]):
        previous = rows.count()
        page.locator("#editor_component_1 .js-editor-add-item:visible").click()
        page.wait_for_function(
            "([selector, previous]) => document.querySelectorAll(selector).length > previous",
            arg=[row_selector, previous])
    for index, item in enumerate(prepared["items"]):
        row = rows.nth(index)
        row.locator(".single-item .js-item-input").fill(
            item["label"]["text"])
        _upload_editor_image(page, row, item["label"]["image"])

    image = page.locator("#big_editor_image")
    image.scroll_into_view_if_needed()
    page.wait_for_timeout(200)
    markers = page.locator("#editor_component_0 .js-editor-image-marker")
    if markers.count() < len(prepared["items"]):
        raise RuntimeError(
            f"Labelled diagram pin 數不足：{markers.count()}/{len(prepared['items'])}。")
    image_box = image.bounding_box()
    if not image_box:
        raise RuntimeError("無法量測 Labelled diagram 底圖位置。")
    for index in reversed(range(len(prepared["items"]))):
        marker = markers.nth(index)
        marker_box = marker.bounding_box()
        if not marker_box:
            raise RuntimeError(f"第 {index + 1} 個 pin 不可見。")
        item = prepared["items"][index]
        target_x = image_box["x"] + image_box["width"] * item["x"]
        target_y = image_box["y"] + image_box["height"] * item["y"]
        page.mouse.move(
            marker_box["x"] + marker_box["width"] / 2,
            marker_box["y"] + marker_box["height"] / 2)
        page.mouse.down()
        page.mouse.move(target_x, target_y, steps=12)
        page.mouse.up()
    page.wait_for_timeout(250)


def _fill_content(page, content: dict, prepared: dict):
    """依 schema 將已驗證內容填進 Wordwall 編輯器。"""
    title = content.get("title", "")
    if title:
        page.locator("input.js-activity-title").fill(title)
    editor_mode = prepared.get("editor_mode")
    if editor_mode:
        page.locator(f"#option_mode{editor_mode}").check()
        page.wait_for_timeout(250)
    if prepared["schema"] == "quiz":
        _fill_quiz_content(page, prepared)
    elif prepared["schema"] == "pair":
        _fill_pair_content(page, prepared)
    elif prepared["schema"] == "group":
        _fill_group_content(page, prepared)
    elif prepared["schema"] == "fixed_group":
        _fill_group_content(page, prepared, rename_titles=False)
    elif prepared["schema"] == "single":
        _fill_single_content(page, prepared)
    elif prepared["schema"] == "cloze":
        _fill_cloze_content(page, prepared)
    elif prepared["schema"] == "diagram":
        _fill_diagram_content(page, prepared)
    else:
        raise NotImplementedError(f"尚未實作內容模型: {prepared['schema']}")


def _verify_editor_content(page, prepared: dict) -> dict:
    """回讀編輯器結構；不按 Done，不建立線上活動。"""
    expected_items = prepared["item_count"]
    if prepared["schema"] == "quiz":
        rows = page.locator(".quiz-item")
        actual_items = rows.count()
        correct_marks = page.locator(
            ".quiz-item .js-question-check .js-toggle-label.checked").count()
        if actual_items < expected_items or correct_marks < expected_items:
            raise RuntimeError(
                f"Quiz 編輯器回讀不符：題目 {actual_items}/{expected_items}，"
                f"正解 {correct_marks}/{expected_items}。")
    elif prepared["schema"] == "pair":
        rows = page.locator(".js-editor-child-items.double-item")
        actual_items = rows.count()
        if actual_items < expected_items:
            raise RuntimeError(
                f"Pair 編輯器回讀不符：配對 {actual_items}/{expected_items}。")
        correct_marks = None
    elif prepared["schema"] in ("group", "fixed_group"):
        groups = page.locator("#editor_component_0 .js-group-component")
        actual_groups = groups.count()
        actual_items = sum(
            groups.nth(index).locator(
                ":scope > div > .js-editor-child-items > .js-item").count()
            for index in range(actual_groups))
        if (actual_groups < prepared["group_count"]
                or actual_items < expected_items):
            raise RuntimeError(
                f"Group 編輯器回讀不符：群組 {actual_groups}/{prepared['group_count']}，"
                f"項目 {actual_items}/{expected_items}。")
        correct_marks = None
    elif prepared["schema"] == "single":
        rows = page.locator(
            "#editor_component_0 > .item-collection > "
            ".js-editor-child-items > .js-item")
        actual_items = rows.count()
        if actual_items < expected_items:
            raise RuntimeError(
                f"Single 編輯器回讀不符：項目 {actual_items}/{expected_items}。")
        correct_marks = None
    elif prepared["schema"] == "cloze":
        rows = page.locator(
            "#editor_component_0 > .item-collection > .js-editor-child-items "
            "> .complete-the-sentence-editor-wrapper")
        actual_items = rows.count()
        actual_correct = sum(
            rows.nth(index).locator(".js-missing-words > .word").count()
            for index in range(actual_items))
        actual_wrong = sum(
            rows.nth(index).locator(".js-wrong-words > .word").count()
            for index in range(actual_items))
        expected_correct = sum(
            len(item["gaps"]) for item in prepared["items"])
        expected_wrong = sum(
            len(item["wrong_answers"]) for item in prepared["items"])
        if (actual_items < expected_items
                or actual_correct < expected_correct
                or actual_wrong < expected_wrong):
            raise RuntimeError(
                f"Cloze 編輯器回讀不符：頁面 {actual_items}/{expected_items}，"
                f"缺字 {actual_correct}/{expected_correct}，"
                f"錯誤選項 {actual_wrong}/{expected_wrong}。")
        correct_marks = actual_correct
    elif prepared["schema"] == "diagram":
        rows = page.locator(
            "#editor_component_1 > .item-collection > "
            ".js-editor-child-items > .js-item")
        markers = page.locator(
            "#editor_component_0 .js-editor-image-marker:visible")
        actual_items = rows.count()
        if actual_items < expected_items or markers.count() < expected_items:
            raise RuntimeError(
                f"Diagram 編輯器回讀不符：標籤 {actual_items}/{expected_items}，"
                f"pin {markers.count()}/{expected_items}。")
        image = page.locator("#big_editor_image")
        image_box = image.bounding_box()
        if not image_box:
            raise RuntimeError("無法回讀 Labelled diagram 底圖位置。")
        for index, expected in enumerate(prepared["items"]):
            marker_box = markers.nth(index).bounding_box()
            if not marker_box:
                raise RuntimeError(f"無法回讀第 {index + 1} 個 pin。")
            actual_x = ((marker_box["x"] + marker_box["width"] / 2
                         - image_box["x"]) / image_box["width"])
            actual_y = ((marker_box["y"] + marker_box["height"] / 2
                         - image_box["y"]) / image_box["height"])
            if (abs(actual_x - expected["x"]) > 0.04
                    or abs(actual_y - expected["y"]) > 0.04):
                raise RuntimeError(
                    f"第 {index + 1} 個 pin 座標回讀不符："
                    f"({actual_x:.3f}, {actual_y:.3f}) / "
                    f"({expected['x']:.3f}, {expected['y']:.3f})。")
        correct_marks = None
    else:
        raise NotImplementedError(f"尚未實作回讀模型: {prepared['schema']}")
    visible_images = page.locator(
        ".js-item-image:visible, .js-question-box .js-item-image:visible").count()
    if visible_images < prepared["image_count"]:
        raise RuntimeError(
            f"圖片回讀不符：{visible_images}/{prepared['image_count']}。")
    return {
        "status": "editor-check-ok",
        "template": prepared["template"],
        "schema": prepared["schema"],
        "item_count": expected_items,
        "group_count": prepared.get("group_count"),
        "image_count": prepared["image_count"],
        "correct_marks": correct_marks,
        "saved": False,
    }


def _save_and_get_url(page, title: str = "") -> str:
    """按下 Done 完成建立,只在取得正式 /resource/ 網址後回傳。"""
    page.locator("button.js-done-button").click()
    try:
        page.wait_for_url(re.compile(r"/resource/\d+"), timeout=30000,
                          wait_until="domcontentloaded")
        return page.url
    except Exception as navigation_error:
        # 某些版本以 AJAX 儲存後不立即換頁；到 My Activities 反查正式網址。
        page.goto(f"{BASE}/myactivities", wait_until="networkidle")
        matches = page.locator("a[href*='/resource/']").filter(
            has_text=title).all() if title else []
        for link in matches:
            href = link.get_attribute("href") or ""
            if re.search(r"/resource/\d+", href):
                return href if href.startswith("http") else f"{BASE}{href}"
        raise RuntimeError(
            "按下 Done 後找不到正式 /resource/ 活動網址。") from navigation_error


# ======================================================================
# 指令:assign —— 建立學生作業並取得連結
# ======================================================================
def _assignment_url_from_page(page) -> str:
    """從作業完成畫面找出學生專用 /play/ 連結。"""
    values = page.locator("input").evaluate_all(
        "els => els.map(e => e.value || '').filter(Boolean)")
    hrefs = page.locator("a").evaluate_all(
        "els => els.map(e => e.href || '').filter(Boolean)")
    body = page.locator("body").inner_text()
    candidates = values + hrefs + re.findall(
        r"https?://(?:www\.)?wordwall\.net/play/[^\s\"'<>]+", body)
    for value in candidates:
        if re.match(r"^https?://(?:www\.)?wordwall\.net/play/", value):
            return value
        if value.startswith("/play/"):
            return f"{BASE}{value}"
    raise RuntimeError("作業已建立,但找不到學生 /play/ 連結。")


def cmd_assign(args):
    """把一個活動設成學生作業,取得學生專用分享連結。"""
    if not re.match(
            r"^https://(?:www\.)?wordwall\.net/resource/", args.activity_url):
        die("--activity-url 必須是 https://wordwall.net/resource/... 網址。")
    if args.deadline_time and not re.match(
            r"^(?:[01]\d|2[0-3]):[0-5]\d$", args.deadline_time):
        die("--deadline-time 格式必須是 HH:MM。")

    sync_playwright = _need_playwright()
    with sync_playwright() as p:
        browser, ctx = _context(p, headless=args.headless)
        page = ctx.new_page()
        if not _verify_logged_in(page):
            browser.close()
            die("登入已失效,請先重新 login。", code=2)
        try:
            page.goto(args.activity_url, wait_until="networkidle")
            page.locator(".js-assignment-button:visible").first.click()
            title = page.locator(".js-results-title")
            title.wait_for(state="visible", timeout=15000)

            register_selector = (
                "#register_name" if args.registration == "name"
                else "#register_anon")
            page.locator(register_selector).click()

            if args.deadline:
                deadline_value = _deadline_for_wordwall(args.deadline)
                page.locator('input[name="deadline"][value="1"]').click()
                page.locator(".js-deadline-date").fill(deadline_value)
                page.locator(".js-deadline-time").select_option(
                    label=args.deadline_time)
            else:
                page.locator("#deadline_none").click()

            _set_checkbox(page, "#gameover_review", args.show_answers)
            _set_checkbox(page, "#gameover_leaderboard", args.leaderboard)
            _set_checkbox(page, "#gameover_restart", args.start_again)
            if args.title:
                title.fill(args.title)

            settings = {
                "activity_url": page.url,
                "title": title.input_value(),
                "registration": args.registration,
                "deadline": args.deadline,
                "deadline_time": args.deadline_time if args.deadline else None,
                "show_answers": args.show_answers,
                "leaderboard": args.leaderboard,
                "start_again": args.start_again,
            }
            if args.dry_run:
                print(json.dumps({"status": "dry-run-ok", **settings},
                                 ensure_ascii=False, indent=2))
                return

            page.locator(".js-next-start").click()
            page.wait_for_timeout(1200)
            assignment_url = _assignment_url_from_page(page)
            print(json.dumps({
                "status": "created",
                "assignment_url": assignment_url,
                **settings,
            }, ensure_ascii=False, indent=2))
        except Exception as e:  # noqa
            _dump_debug(page, "assign_fail")
            die(f"設定作業失敗。原始錯誤:{e}", code=3)
        finally:
            browser.close()


# ======================================================================
# 指令:results —— 列出作業或匯出 Excel / CSV
# ======================================================================
def _result_rows(page) -> list[dict]:
    """讀取 My Results 的作業 ID、名稱與作答人數,不讀學生姓名。"""
    rows = []
    items = page.locator("a.js-result-item")
    for index in range(items.count()):
        item = items.nth(index)
        href = item.get_attribute("href") or ""
        match = re.search(r"/result/a/(\d+)", href)
        title = item.locator(".js-item-name").inner_text().strip()
        players = item.locator(".js-item-players").inner_text().strip()
        rows.append({
            "assignment_id": match.group(1) if match else "",
            "title": title,
            "players": players,
            "is_open": "is-open" in (item.get_attribute("class") or ""),
            "index": index,
        })
    return rows


def _find_result_row(rows: list[dict], assignment_id: str | None,
                     title_query: str | None) -> dict:
    """用作業 ID 或名稱片段找唯一一筆結果。"""
    if assignment_id:
        matches = [row for row in rows
                   if row["assignment_id"] == str(assignment_id)]
    elif title_query:
        needle = title_query.casefold()
        matches = [row for row in rows
                   if needle in row["title"].casefold()]
    else:
        raise ValueError("匯出時必須提供 --assignment-id 或 --title。")
    if not matches:
        raise ValueError("找不到指定的 Wordwall 作業結果。")
    if len(matches) > 1:
        choices = ", ".join(
            f'{row["assignment_id"]}:{row["title"]}' for row in matches[:8])
        raise ValueError(f"找到多筆符合結果,請改用 --assignment-id:{choices}")
    return matches[0]


def _save_result_download(download, output_value: str | None,
                          requested_format: str) -> Path:
    """將 Wordwall 下載檔存到指定位置或安全的使用者 Downloads。"""
    suggested = download.suggested_filename
    output = (Path(output_value).expanduser() if output_value else
              Path.home() / "Downloads" / "wordwall-results")
    if output.suffix:
        target = output
    else:
        target = output / suggested
    if target.suffix.lower() not in {".xlsx", ".csv"}:
        target = target.with_suffix(f".{requested_format}")
    target = target.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    download.save_as(str(target))
    return target


def _export_result(page, row: dict, requested_format: str,
                   output_value: str | None) -> Path:
    """打開指定作業列的選單,下載 Excel 或 CSV。"""
    item = page.locator("a.js-result-item").nth(row["index"])
    item.locator(".js-item-menu").click()
    export_item = page.locator(".js-export-item:visible")
    export_item.wait_for(state="visible", timeout=10000)

    try:
        with page.expect_download(timeout=7000) as download_info:
            export_item.click()
        download = download_info.value
    except Exception as first_error:  # 格式選擇對話框版本
        pattern = re.compile(
            r"CSV" if requested_format == "csv" else r"Excel|XLSX",
            re.IGNORECASE)
        format_control = page.locator(
            "button:visible, a:visible, [role=button]:visible, label:visible"
        ).filter(has_text=pattern)
        if not format_control.count():
            raise RuntimeError(
                f"匯出按鈕未開始下載,也找不到 {requested_format} 格式選項:"
                f"{first_error}") from first_error
        with page.expect_download(timeout=15000) as download_info:
            format_control.first.click()
        download = download_info.value

    suffix = Path(download.suggested_filename).suffix.lower()
    expected = f".{requested_format}"
    if suffix and suffix != expected:
        raise RuntimeError(
            f"Wordwall 回傳 {suffix} 檔,與要求的 {expected} 不符。")
    return _save_result_download(download, output_value, requested_format)


def cmd_results(args):
    """列出作業或從 My Results 匯出成績檔。"""
    sync_playwright = _need_playwright()
    with sync_playwright() as p:
        browser, ctx = _context(p, headless=args.headless)
        page = ctx.new_page()
        if not _verify_logged_in(page):
            browser.close()
            die("登入已失效,請先重新 login。", code=2)
        try:
            page.goto(f"{BASE}/myresults", wait_until="networkidle")
            rows = _result_rows(page)
            if args.results_action == "list":
                if args.title:
                    needle = args.title.casefold()
                    rows = [row for row in rows
                            if needle in row["title"].casefold()]
                for row in rows:
                    row.pop("index", None)
                print(json.dumps(rows, ensure_ascii=False, indent=2))
                return

            row = _find_result_row(
                rows, args.assignment_id, args.title)
            if args.dry_run:
                row = {key: value for key, value in row.items()
                       if key != "index"}
                print(json.dumps({
                    "status": "dry-run-ok",
                    "format": args.format,
                    "output": args.output,
                    "result": row,
                }, ensure_ascii=False, indent=2))
                return

            target = _export_result(
                page, row, args.format, args.output)
            print(json.dumps({
                "status": "downloaded",
                "assignment_id": row["assignment_id"],
                "title": row["title"],
                "format": args.format,
                "output": str(target),
            }, ensure_ascii=False, indent=2))
        except Exception as e:  # noqa
            _dump_debug(page, "results_fail")
            die(f"讀取或匯出結果失敗。原始錯誤:{e}", code=3)
        finally:
            browser.close()


# ======================================================================
# 參數解析
# ======================================================================
def build_parser():
    parser = argparse.ArgumentParser(
        prog="wordwall.py",
        description="用 CLI 控制 Wordwall（供 Codex、Claude Code 等 Agent 搭配 SKILL.md 使用）。")
    sub = parser.add_subparsers(dest="command", required=True)

    p_doctor = sub.add_parser("doctor", help="檢查安裝、瀏覽器、登入與選用 PDF 元件")
    p_doctor.add_argument("--login", action="store_true",
                          help="連線驗證目前 Wordwall 登入狀態")
    p_doctor.add_argument("--pdf", action="store_true",
                          help="同時檢查 PDF 截圖選用元件")
    p_doctor.add_argument("--skip-browser", action="store_true",
                          help="只檢查套件，不實際啟動 Chromium")
    p_doctor.set_defaults(func=cmd_doctor)

    p_login = sub.add_parser("login", help="在互動終端開瀏覽器手動登入並存下 session")
    p_login.set_defaults(func=cmd_login)

    p_chrome_login = sub.add_parser(
        "chrome-login", help="開啟本工具專用的真實 Chrome，供本人登入")
    p_chrome_login.add_argument("--port", type=int, default=DEFAULT_CDP_PORT,
                                help=f"Chrome 除錯埠（預設 {DEFAULT_CDP_PORT}；占用時請換一個）")
    p_chrome_login.add_argument("--profile-dir", default=str(CHROME_LOGIN_PROFILE),
                                help=f"專用 Chrome 個人資料夾（預設 {CHROME_LOGIN_PROFILE}）")
    p_chrome_login.add_argument("--chrome-path", help="選用 Chrome 執行檔路徑")
    p_chrome_login.set_defaults(func=cmd_chrome_login)

    p_grab = sub.add_parser("grab-session",
                            help="從你已登入的真實 Chrome 複製 Wordwall session(繞過 Google 封鎖)")
    p_grab.add_argument("--cdp-url",
                        help="進階用法：明確指定既有 Chrome 除錯網址；省略時只讀本工具 chrome-login 紀錄")
    p_grab.set_defaults(func=cmd_grab_session)

    p_check = sub.add_parser("check", help="檢查登入是否還有效")
    p_check.set_defaults(func=cmd_check)

    p_tpl = sub.add_parser("templates", help="列出範本 schema、媒體能力與實作狀態")
    p_tpl.add_argument("--json", action="store_true",
                       help="輸出機器可讀 JSON")
    p_tpl.set_defaults(func=cmd_templates)

    p_rec = sub.add_parser("recommend", help="依意圖與媒體型態推薦範本")
    p_rec.add_argument("--intent", help="自然語言關鍵字，例如 圖片配對、迷宮")
    p_rec.add_argument("--schema",
                       choices=sorted({info["schema"]
                                       for info in TEMPLATE_CATALOG.values()}),
                       help="內容模型")
    p_rec.add_argument("--media",
                       choices=("text", "text-image", "image-image"),
                       help="媒體組合")
    p_rec.add_argument("--implemented-only", action="store_true",
                       help="只列出目前 CLI 已能建立的範本")
    p_rec.set_defaults(func=cmd_recommend)

    p_plan = sub.add_parser(
        "plan", help="把自然語言轉成範本、三級素材策略與安全預檢計畫")
    p_plan.add_argument("--request", required=True,
                        help="自然語言出題需求")
    p_plan.add_argument("--level",
                        choices=("auto", "text", "screenshot", "ai-image"),
                        default="auto", help="素材層級；預設自動採最低足夠層級")
    p_plan.add_argument("--template", choices=sorted(TEMPLATE_CATALOG),
                        help="強制指定 Wordwall 範本")
    p_plan.add_argument("--content",
                        help="選用內容 JSON；提供時一併 dry-run 預檢")
    p_plan.add_argument("--assets",
                        help="選用素材 manifest JSON；提供時驗證定稿圖與品質覆核")
    p_plan.add_argument("--output",
                        help="選用輸出 plan JSON 檔；省略時只印到終端")
    p_plan.set_defaults(func=cmd_plan)

    p_pdf = sub.add_parser("pdf-screenshot",
                           help="將 PDF 指定頁或指定區域輸出為 PNG")
    p_pdf.add_argument("--input", required=True, help="來源 PDF 路徑")
    p_pdf.add_argument("--page", required=True, type=int,
                       help="頁碼，從 1 開始")
    p_pdf.add_argument("--output", required=True,
                       help="輸出 PNG 檔或資料夾")
    p_pdf.add_argument("--crop",
                       help="選用裁切座標 x0,y0,x1,y1，單位為 PDF 點")
    p_pdf.add_argument("--scale", type=float, default=3.0,
                       help="渲染倍率，預設 3.0")
    p_pdf.add_argument("--padding", type=int, default=16,
                       help="白色邊界像素，預設 16")
    p_pdf.set_defaults(func=cmd_pdf_screenshot)

    p_ins = sub.add_parser("inspect", help="登入後 dump 指定頁面的 DOM(用來校正選擇器)")
    p_ins.add_argument("--url", required=True, help="要檢視的網址")
    p_ins.add_argument("--headless", action="store_true", help="不開視窗(預設開視窗方便觀察)")
    p_ins.set_defaults(func=cmd_inspect)

    p_new = sub.add_parser("create", help="依內容 JSON 建立 Quiz,支援每題圖片")
    p_new.add_argument("--content", required=True, help="內容 JSON 檔路徑(見 examples/)")
    p_new.add_argument("--template", help="覆寫 JSON 內的範本代號")
    p_new.add_argument("--headless", action="store_true")
    create_mode = p_new.add_mutually_exclusive_group()
    create_mode.add_argument("--dry-run", action="store_true",
                             help="只驗證 JSON 與圖片路徑,不登入、不建立活動")
    create_mode.add_argument("--editor-check", action="store_true",
                             help="登入並填入編輯器後回讀,不按 Done、不建立活動")
    p_new.set_defaults(func=cmd_create)

    p_asg = sub.add_parser("assign", help="把活動設成學生作業並取得連結")
    p_asg.add_argument("--activity-url", required=True, help="活動網址")
    p_asg.add_argument("--title", help="My Results 顯示的作業名稱")
    p_asg.add_argument("--registration", choices=("name", "anonymous"),
                       default="name", help="學生輸入姓名或匿名作答")
    p_asg.add_argument("--deadline", help="截止日期 YYYY-MM-DD;省略表示無期限")
    p_asg.add_argument("--deadline-time", default="23:59",
                       help="截止時間 HH:MM(預設 23:59)")
    p_asg.add_argument("--show-answers", action=argparse.BooleanOptionalAction,
                       default=True, help="結束後顯示答案")
    p_asg.add_argument("--leaderboard", action=argparse.BooleanOptionalAction,
                       default=False, help="顯示排行榜")
    p_asg.add_argument("--start-again", action=argparse.BooleanOptionalAction,
                       default=True, help="允許重新作答")
    p_asg.add_argument("--dry-run", action="store_true",
                       help="填入並驗證設定,不按 Start、不建立作業")
    p_asg.add_argument("--headless", action="store_true")
    p_asg.set_defaults(func=cmd_assign)

    p_res = sub.add_parser("results", help="列出作業或匯出 Excel / CSV")
    p_res_sub = p_res.add_subparsers(dest="results_action", required=True)
    p_res_list = p_res_sub.add_parser("list", help="列出作業 ID、名稱與作答人數")
    p_res_list.add_argument("--title", help="只列出名稱含此文字的作業")
    p_res_list.add_argument("--headless", action="store_true")
    p_res_export = p_res_sub.add_parser("export", help="匯出指定作業結果")
    target = p_res_export.add_mutually_exclusive_group(required=True)
    target.add_argument("--assignment-id", help="My Results 的作業 ID")
    target.add_argument("--title", help="作業名稱片段(必須只符合一筆)")
    p_res_export.add_argument("--format", choices=("xlsx", "csv"),
                              default="xlsx")
    p_res_export.add_argument("--output",
                              help="輸出檔或資料夾;預設 Downloads/wordwall-results")
    p_res_export.add_argument("--dry-run", action="store_true",
                              help="只確認目標作業,不下載學生資料")
    p_res_export.add_argument("--headless", action="store_true")
    p_res.set_defaults(func=cmd_results)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
