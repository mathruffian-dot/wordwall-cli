"""自然語言 Wordwall 出題規劃器與三級素材決策。"""

from __future__ import annotations

import re
from pathlib import Path

from wordwall_catalog import TEMPLATE_CATALOG


LEVELS = {
    "text": {"number": 1, "label": "純文字出題"},
    "screenshot": {"number": 2, "label": "截圖出題"},
    "ai-image": {"number": 3, "label": "AI 生成圖片出題"},
}


TEMPLATE_RULES = (
    (r"標籤圖|標示圖|標記圖|labelled diagram", "labelled_diagram"),
    (r"是非|真假|true or false", "true_or_false"),
    (r"翻牌|matching pairs", "matching_pairs"),
    (r"配對|match up|圖對圖", "match_up"),
    (r"分類|分組|group sort", "group_sort"),
    (r"排序|rank order", "rank_order"),
    (r"填空|完成句子|complete the sentence", "complete_the_sentence"),
    (r"開箱|open the box", "open_the_box"),
    (r"轉盤|輪盤|spin the wheel|random wheel", "spin_the_wheel"),
    (r"記憶卡|字卡|flash cards", "flash_cards"),
    (r"遊戲節目|gameshow", "gameshow_quiz"),
    (r"迷宮|maze", "maze_chase"),
    (r"測驗|選擇題|quiz|題目", "quiz"),
)


AI_NOVELTY_RULES = {
    "故事與角色決策": r"故事|劇情|角色|任務|冒險|對話|情境決策",
    "漫畫與連續分鏡": r"漫畫|分鏡|連環|下一幕|前後畫面",
    "視覺解謎與密碼": r"解謎|謎題|密室|密碼|找出犯人|視覺線索",
    "多視角與空間推理": r"多視角|不同視角|俯視|側視|第一人稱|空間場景",
    "遮擋與隱藏結構": r"遮擋|遮住|隱藏|露出一部分|補全畫面",
    "影子倒影與光線推論": r"影子|倒影|鏡像|反射|光線|照明",
    "狀態變化與因果": r"變化過程|狀態變化|前後變化|時間序列|變形過程",
    "視覺錯誤與矛盾": r"找錯|不合理|矛盾|視覺錯覺|不可能圖形",
    "奇幻或不可實拍場景": r"奇幻|擬人|太空|未來世界|微觀世界|夢境",
    "社會情緒與非語文線索": r"表情|情緒|肢體語言|合作|衝突|同理",
    "視覺資料與虛構文件": r"虛構菜單|虛構票券|虛構地圖|收據|儀表板|任務海報",
    "尺度估測與沉浸場景": r"尺度估測|距離判斷|容量估測|沉浸場景|巨人視角|微縮世界",
    "規則世界與反例探索": r"異世界規則|反例世界|如果.*會怎樣|改變一條規則",
}


PRECISION_RULE = re.compile(
    r"幾何|座標|函數圖|統計圖|尺規|刻度|精確比例|公式|數線|證明圖|工程圖",
    re.IGNORECASE)
SCREENSHOT_RULE = re.compile(
    r"截圖|PDF|考卷|題庫|版面|掃描|照片|幾何|圖表|座標|函數圖|統計圖",
    re.IGNORECASE)
IMAGE_RULE = re.compile(
    r"圖片|圖形|插圖|照片|漫畫|場景|視覺|影子|倒影|地圖|圖表",
    re.IGNORECASE)
IMAGE_IMAGE_RULE = re.compile(
    r"圖片配圖片|圖對圖|都是圖片|圖片選項|選項.*圖片|只能用圖形|圖形.*判別",
    re.IGNORECASE)


def _infer_template(request: str, requested_template: str | None) -> str:
    if requested_template:
        if requested_template not in TEMPLATE_CATALOG:
            raise ValueError(f"未知範本: {requested_template}")
        return requested_template
    for pattern, template in TEMPLATE_RULES:
        if re.search(pattern, request, re.IGNORECASE):
            return template
    return "quiz"


def _infer_media(request: str) -> str:
    if IMAGE_IMAGE_RULE.search(request):
        return "image-image"
    if IMAGE_RULE.search(request) or SCREENSHOT_RULE.search(request):
        return "text-image"
    return "text"


def _novelty_matches(request: str) -> list[str]:
    return [name for name, pattern in AI_NOVELTY_RULES.items()
            if re.search(pattern, request, re.IGNORECASE)]


def _asset_level(request: str, requested_level: str,
                 media: str) -> tuple[str, dict]:
    novelty = _novelty_matches(request)
    precision = bool(PRECISION_RULE.search(request))
    explicitly_ai = requested_level == "ai-image" or bool(
        re.search(r"AI.*生圖|AI.*圖片|生成圖片|生圖", request,
                  re.IGNORECASE))
    gate = {
        "requested": explicitly_ai,
        "passed": bool(novelty),
        "novelty_reasons": novelty,
        "precision_overlay_required": precision and bool(novelty),
    }

    if requested_level == "text":
        level = "text"
    elif requested_level == "screenshot":
        level = "screenshot"
    elif requested_level == "ai-image":
        level = "ai-image" if novelty else "screenshot"
        if not novelty:
            gate["decision"] = "downgraded-to-screenshot"
            gate["reason"] = "未通過創意必要性門檻；精準或傳統圖形不使用 AI 生圖。"
    elif novelty and explicitly_ai:
        level = "ai-image"
    elif SCREENSHOT_RULE.search(request) or media != "text":
        level = "screenshot"
    else:
        level = "text"

    if level == "ai-image":
        gate["decision"] = "approved"
        gate["reason"] = "需求包含傳統考卷或精準繪圖難以表達的視覺敘事。"
    elif not explicitly_ai:
        gate["decision"] = "not-requested"
        gate["reason"] = "採用能完成需求的最低素材層級。"
    return level, gate


def _layout_for(template: str, schema: str, level: str) -> dict:
    if level == "text":
        return {"type": "text-fields", "composite": False,
                "instruction": "題幹與答案直接使用 Wordwall 文字欄位。"}
    if schema == "quiz":
        return {
            "type": "composite-question-image",
            "composite": True,
            "instruction": "把題幹與所有視覺選項合成一張 PNG；Wordwall 答案使用 A/B/C/D。",
        }
    if schema in ("pair", "pair_mode") or template == "matching_pairs":
        return {
            "type": "paired-assets-then-capture",
            "composite": False,
            "instruction": "先完成每個配對端圖片，再截取定稿資產，依左右端放入 Pair JSON。",
        }
    if schema == "diagram":
        return {
            "type": "base-image-with-normalized-pins",
            "composite": False,
            "instruction": "使用一張底圖，標籤以 x/y 0..1 座標定位。",
        }
    return {
        "type": "individual-item-images",
        "composite": False,
        "instruction": "每個項目使用獨立定稿 PNG，避免在 Wordwall 內重新排版。",
    }


def _asset_steps(level: str, layout: dict, gate: dict) -> list[str]:
    if level == "text":
        return [
            "撰寫題幹、選項與正解。",
            "檢查數學符號、答案唯一性與文字長度。",
        ]
    if level == "screenshot":
        steps = [
            "優先取得既有題庫、考卷、PDF 或精準繪圖來源。",
            "裁切時保留完整題幹、選項標記、幾何圖與必要留白。",
        ]
        if layout["composite"]:
            steps.append("將題幹與全部圖片選項排成一張定稿 PNG。")
        else:
            steps.append("將每個需要上傳的區塊輸出成定稿 PNG。")
        return steps

    steps = [
        "確認 AI 圖片確實用於故事、漫畫、解謎或其他創意必要情境。",
        "載入 imagegen skill 並呼叫 image_gen 內建工具實際產圖；不得只撰寫 prompt 或靜默降級。",
        "先生成無答案洩漏、風格一致的場景或選項素材。",
        "目視檢查生成結果，確認數學內容、文字可讀性、構圖與答案洩漏後再定稿。",
        "把數學文字、精準線段、刻度與答案標記用傳統排版覆蓋，不依賴 AI 畫準。",
    ]
    if layout["composite"]:
        steps.append("把題幹與所有視覺選項合成一張最終題圖，再截圖定稿。")
    else:
        steps.append("逐張檢查配對資產後截圖定稿，再放入 Wordwall。")
    if gate.get("precision_overlay_required"):
        steps.append("此題同時含精準數學元素，必須採 AI 場景＋傳統精準覆圖的混合流程。")
    return steps


def _content_contract(template: str, schema: str, layout: dict) -> dict:
    if schema == "quiz":
        question = ("文字題幹" if layout["type"] == "text-fields" else
                    {"text": "請看圖作答", "image": "question.png"})
        item = {
            "question": question,
            "answers": ["A", "B", "C", "D"],
            "correct": 0,
        }
        return {"template": template,
                "items": [dict(item) for _ in range(
                    max(1, TEMPLATE_CATALOG[template]["min"]))]}
    if schema in ("pair", "pair_mode"):
        return {"template": template, "mode": "different",
                "pairs": [
                    {"left": {"image": f"left-{index}.png"},
                     "right": {"image": f"right-{index}.png"}}
                    for index in range(1, max(
                        3, TEMPLATE_CATALOG[template]["min"]) + 1)]}
    if template == "true_or_false":
        return {"template": template, "items": [
            {"statement": "正確敘述", "correct": True},
            {"statement": "錯誤敘述", "correct": False},
        ]}
    if schema == "group":
        return {"template": template,
                "groups": [
                    {"title": "第一組", "items": ["項目一"]},
                    {"title": "第二組", "items": ["項目二"]},
                ]}
    if schema == "diagram":
        return {"template": template, "image": "diagram.png",
                "labels": [
                    {"text": "標籤 A", "x": 0.2, "y": 0.3},
                    {"text": "標籤 B", "x": 0.5, "y": 0.5},
                    {"text": "標籤 C", "x": 0.8, "y": 0.7},
                ]}
    if template == "complete_the_sentence":
        return {"template": template,
                "pages": [{"sentence": "答案是{{42}}。"}]}
    return {"template": template, "mode": "simple",
            "items": ["項目一", "項目二", "項目三"]}


def _asset_manifest_contract(level: str, layout: dict) -> dict:
    if level == "text":
        return {
            "asset_level": "text",
            "generation_method": "none",
            "final_assets": [],
            "math_verified": True,
            "answer_leak_checked": True,
            "mobile_checked": True,
        }
    method = ("builtin-imagegen" if level == "ai-image"
              else "existing-or-screenshot")
    role = ("composite-question" if layout["composite"]
            else "final-item-or-pair-side")
    contract = {
        "asset_level": level,
        "generation_method": method,
        "source_files": [],
        "final_assets": [{"role": role, "path": "final.png"}],
        "capture_finalized": True,
        "math_verified": True,
        "answer_leak_checked": True,
        "mobile_checked": True,
    }
    if level == "ai-image":
        contract["prompt"] = "保存實際使用的完整生圖提示詞"
    return contract


def validate_asset_manifest(manifest: dict, base_dir: Path,
                            plan: dict) -> dict:
    """確認素材層級、定稿檔與必要品質覆核都有紀錄。"""
    expected_level = plan["decision"]["asset_level"]
    if manifest.get("asset_level") != expected_level:
        raise ValueError(
            f"asset manifest 層級應為 {expected_level}。")
    for field in ("math_verified", "answer_leak_checked", "mobile_checked"):
        if manifest.get(field) is not True:
            raise ValueError(f"asset manifest 必須確認 {field}=true。")
    if expected_level == "text":
        return {"status": "asset-manifest-ok", "asset_count": 0,
                "asset_level": expected_level}

    assets = manifest.get("final_assets") or []
    if not assets:
        raise ValueError("asset manifest 必須至少有一個 final_assets。")
    resolved = []
    roles = []
    for index, asset in enumerate(assets, start=1):
        if not isinstance(asset, dict) or not asset.get("path"):
            raise ValueError(f"第 {index} 個 final asset 缺少 path。")
        path = Path(asset["path"]).expanduser()
        if not path.is_absolute():
            path = base_dir / path
        path = path.resolve()
        if not path.is_file():
            raise ValueError(f"找不到定稿素材: {path}")
        resolved.append(str(path))
        roles.append(asset.get("role", ""))
    if (plan["layout"]["composite"]
            and "composite-question" not in roles):
        raise ValueError("整張題圖模式必須有 role=composite-question。")
    if manifest.get("capture_finalized") is not True:
        raise ValueError("圖片素材必須完成截圖／合成定稿(capture_finalized=true)。")
    if expected_level == "ai-image":
        if not str(manifest.get("prompt", "")).strip():
            raise ValueError("第三級素材必須保存實際生圖 prompt。")
        if manifest.get("generation_method") not in {
                "builtin-imagegen", "local-draw-override"}:
            raise ValueError(
                "第三級 generation_method 必須是 builtin-imagegen "
                "或 local-draw-override。")
    return {"status": "asset-manifest-ok",
            "asset_count": len(resolved),
            "asset_level": expected_level,
            "files": resolved}


def build_question_plan(request: str, requested_level: str = "auto",
                        requested_template: str | None = None) -> dict:
    """把自然語言轉成 Wordwall 範本與三級素材執行計畫。"""
    request = request.strip()
    if not request:
        raise ValueError("request 不可為空白。")
    template = _infer_template(request, requested_template)
    info = TEMPLATE_CATALOG[template]
    media = _infer_media(request)
    level, gate = _asset_level(request, requested_level, media)
    layout = _layout_for(template, info["schema"], level)
    warnings = []
    if not info["implemented"]:
        warnings.append("指定範本的建立器尚未實作，正式建立前必須改選或先開發。")
    if level == "text" and media != "text":
        warnings.append("需求提到圖片，但強制使用純文字層級；請確認是否會遺失判讀資訊。")
    if gate.get("precision_overlay_required"):
        warnings.append("AI 只生成情境底圖；精準數學圖形與標記必須後製。")

    return {
        "status": "plan-ready",
        "request": request,
        "decision": {
            "template": template,
            "schema": info["schema"],
            "implemented": info["implemented"],
            "media": media,
            "asset_level": level,
            "asset_level_number": LEVELS[level]["number"],
            "asset_level_label": LEVELS[level]["label"],
        },
        "ai_novelty_gate": gate,
        "image_generation": {
            "required": level == "ai-image",
            "skill": "imagegen" if level == "ai-image" else None,
            "tool": "image_gen" if level == "ai-image" else None,
            "instruction": (
                "載入 imagegen skill 並呼叫 image_gen 實際產圖；產圖後目視檢查。"
                if level == "ai-image" else "不需要生成圖片。"),
            "unavailable_action": (
                "停止 Level 3，請使用者提供圖片或明確確認降級；不得只輸出 prompt。"
                if level == "ai-image" else None),
        },
        "layout": layout,
        "asset_steps": _asset_steps(level, layout, gate),
        "content_contract": _content_contract(template, info["schema"], layout),
        "asset_manifest_contract": _asset_manifest_contract(level, layout),
        "quality_checks": [
            "數學內容、正解與干擾選項均人工或程式複核。",
            "圖片不洩漏答案，選項視覺風格與資訊量一致。",
            "手機顯示仍可辨識；文字不依賴 AI 圖像內的小字。",
            "第三級素材保存原始提示詞、定稿 PNG 與來源層級。",
            "正式建立前完成 dry-run、editor-check 與使用者確認。",
        ],
        "creative_possibilities": list(AI_NOVELTY_RULES),
        "warnings": warnings,
        "requires_user_confirmation": True,
    }
