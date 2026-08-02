"""Wordwall 範本能力目錄。

schema 描述內容資料結構，media 描述可接受的媒體組合。遊戲外觀不同，
但只要 schema 相同，就能共用同一個建立器。
"""

TEMPLATE_CATALOG = {
    "quiz": {"id": 5, "schema": "quiz", "media": ["text", "text-image", "image-image"], "min": 1, "max": 100, "implemented": True, "description": "一般選擇題", "aliases": ["測驗", "選擇題", "quiz"]},
    "gameshow_quiz": {"id": 69, "schema": "quiz", "media": ["text", "text-image", "image-image"], "min": 2, "max": 100, "implemented": True, "description": "遊戲節目風格選擇題", "aliases": ["遊戲節目", "gameshow"]},
    "maze_chase": {"id": 49, "schema": "quiz", "media": ["text", "text-image", "image-image"], "min": 1, "max": 100, "implemented": True, "description": "迷宮追逐選擇題", "aliases": ["迷宮", "maze"]},
    "flying_fruit": {"id": 82, "schema": "quiz", "media": ["text", "text-image", "image-image"], "min": 1, "max": 100, "implemented": True, "description": "飛果選擇題", "aliases": ["飛果", "flying fruit"]},
    "airplane": {"id": 48, "schema": "quiz", "media": ["text", "text-image", "image-image"], "min": 1, "max": 100, "implemented": True, "description": "飛機選擇題", "aliases": ["飛機", "airplane"]},
    "win_or_lose_quiz": {"id": 78, "schema": "quiz", "media": ["text", "text-image", "image-image"], "min": 3, "max": 20, "implemented": True, "description": "輸贏測驗", "aliases": ["輸贏", "win or lose"]},
    "image_quiz": {"id": 68, "schema": "image_quiz", "media": ["text-image", "image-image"], "min": 1, "max": 50, "implemented": False, "description": "以圖片為主的選擇題", "aliases": ["圖片測驗", "image quiz"]},

    "match_up": {"id": 3, "schema": "pair", "media": ["text", "text-image", "image-image"], "min": 3, "max": 30, "implemented": True, "description": "拖曳配對", "aliases": ["配對", "配對遊戲", "match up"]},
    "find_the_match": {"id": 46, "schema": "pair", "media": ["text", "text-image", "image-image"], "min": 3, "max": 30, "implemented": True, "description": "尋找匹配項", "aliases": ["找配對", "find the match"]},
    "flash_cards": {"id": 76, "schema": "pair", "media": ["text", "text-image", "image-image"], "min": 1, "max": 100, "implemented": True, "description": "雙面記憶卡", "aliases": ["字卡", "記憶卡", "flash cards"]},
    "balloon_pop": {"id": 71, "schema": "pair", "media": ["text", "text-image", "image-image"], "min": 5, "max": 100, "implemented": True, "description": "氣球與火車配對", "aliases": ["刺破氣球", "氣球", "balloon pop"]},
    "matching_pairs": {"id": 25, "schema": "pair_mode", "media": ["text", "text-image", "image-image"], "min": 3, "max": 20, "implemented": True, "description": "相同或不同物品的翻牌配對", "aliases": ["翻牌", "matching pairs"]},
    "flip_tiles": {"id": 75, "schema": "pair_mode", "media": ["text", "text-image", "image-image"], "min": 2, "max": 50, "implemented": False, "description": "單面或雙面翻牌", "aliases": ["翻轉卡片", "flip tiles"]},

    "group_sort": {"id": 2, "schema": "group", "media": ["text", "text-image", "image-image"], "min": 2, "max": 8, "implemented": True, "description": "拖曳分類", "aliases": ["分類", "分組", "group sort"]},
    "speed_sorting": {"id": 81, "schema": "group", "media": ["text", "text-image", "image-image"], "min": 2, "max": 8, "implemented": True, "description": "快速分類", "aliases": ["快速分類", "speed sorting"]},
    "true_or_false": {"id": 35, "schema": "fixed_group", "media": ["text", "text-image"], "min": 2, "max": 30, "implemented": True, "description": "真假分類", "aliases": ["是非題", "真假", "true or false"]},
    "whack_a_mole": {"id": 45, "schema": "fixed_group", "media": ["text", "text-image"], "min": 10, "max": 60, "implemented": False, "description": "正確與錯誤項目的打地鼠", "aliases": ["打地鼠", "whack a mole"]},

    "speaking_cards": {"id": 70, "schema": "single", "media": ["text", "text-image"], "min": 3, "max": 100, "implemented": True, "description": "隨機發卡", "aliases": ["隨機卡", "speaking cards"]},
    "spin_the_wheel": {"id": 8, "schema": "single_mode", "media": ["text", "text-image"], "min": 3, "max": 50, "implemented": True, "description": "簡易轉盤", "aliases": ["轉盤", "輪盤", "spin the wheel"]},
    "random_wheel": {"id": 8, "schema": "single_mode", "media": ["text", "text-image"], "min": 3, "max": 50, "implemented": True, "description": "隨機轉盤", "aliases": ["隨機輪盤", "random wheel"]},
    "open_the_box": {"id": 30, "schema": "single_mode", "media": ["text", "text-image"], "min": 2, "max": 100, "implemented": True, "description": "簡易開箱", "aliases": ["開箱", "open the box"]},
    "rank_order": {"id": 50, "schema": "single", "media": ["text", "text-image"], "min": 3, "max": 30, "implemented": True, "description": "排序項目", "aliases": ["排序", "rank order"]},
    "watch_and_memorize": {"id": 23, "schema": "single", "media": ["text", "text-image"], "min": 7, "max": 40, "implemented": False, "description": "觀看並記憶項目", "aliases": ["觀看並記憶", "watch and memorize"]},

    "complete_the_sentence": {"id": 36, "schema": "clue", "media": ["text", "text-image"], "min": 1, "max": 100, "implemented": True, "description": "句子挖空", "aliases": ["完成句子", "填空", "complete the sentence"]},
    "unjumble": {"id": 72, "schema": "clue", "media": ["text", "text-image"], "min": 1, "max": 50, "implemented": False, "description": "重組句子並可附圖片線索", "aliases": ["句子排列", "unjumble"]},
    "crossword": {"id": 11, "schema": "clue", "media": ["text", "text-image"], "min": 2, "max": 30, "implemented": False, "description": "文字答案與線索", "aliases": ["填字", "crossword"]},
    "type_the_answer": {"id": 89, "schema": "clue", "media": ["text", "text-image"], "min": 1, "max": 30, "implemented": False, "description": "輸入文字答案", "aliases": ["輸入答案", "type the answer"]},
    "type_the_number": {"id": 83, "schema": "clue", "media": ["text", "text-image"], "min": 1, "max": 20, "implemented": False, "description": "輸入數字答案", "aliases": ["輸入數字", "type the number"]},
    "anagram": {"id": 38, "schema": "word", "media": ["text", "text-image"], "min": 1, "max": 100, "implemented": False, "description": "重組字母，可附圖片線索", "aliases": ["拼字遊戲", "anagram"]},
    "hangman": {"id": 73, "schema": "word", "media": ["text", "text-image"], "min": 1, "max": 20, "implemented": False, "description": "猜字，可附圖片線索", "aliases": ["猜字", "hangman"]},
    "wordsearch": {"id": 10, "schema": "word", "media": ["text", "text-image"], "min": 3, "max": 25, "implemented": False, "description": "找字，可附圖片線索", "aliases": ["找字", "wordsearch"]},
    "spell_the_word": {"id": 79, "schema": "word", "media": ["text", "text-image"], "min": 1, "max": 20, "implemented": False, "description": "朗讀或線索拼字", "aliases": ["拼寫單詞", "spell the word"]},
    "word_magnets": {"id": 47, "schema": "text", "media": ["text"], "min": 0, "max": 250, "implemented": False, "description": "文字磁鐵", "aliases": ["連詞造句", "文字磁鐵", "word magnets"]},
    "maths_generator": {"id": 59, "schema": "generator", "media": ["text"], "min": 0, "max": 0, "implemented": False, "description": "Wordwall 內建數學題生成器", "aliases": ["數學題生成器", "maths generator"]},
    "labelled_diagram": {"id": 22, "schema": "diagram", "media": ["text-image", "image-image"], "min": 3, "max": 24, "implemented": True, "description": "底圖與定位標籤", "aliases": ["標記圖表", "標籤圖", "labelled diagram"]},
}


def recommend_templates(schema=None, media=None, intent=None,
                        implemented_only=False):
    """依內容模型、媒體型態或自然語言關鍵字推薦範本。"""
    needle = (intent or "").casefold().strip()
    rows = []
    for key, info in TEMPLATE_CATALOG.items():
        if schema and info["schema"] != schema:
            continue
        if media and media not in info["media"]:
            continue
        if implemented_only and not info["implemented"]:
            continue
        aliases = [key, info["description"], *info.get("aliases", [])]
        score = sum(1 for alias in aliases
                    if needle and (needle in alias.casefold()
                                   or alias.casefold() in needle))
        if needle and score == 0:
            continue
        rows.append({"template": key, **info, "score": score})
    rows.sort(key=lambda row: (-row["score"], not row["implemented"],
                               row["template"]))
    return rows
