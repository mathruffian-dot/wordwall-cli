import tempfile
import unittest
from pathlib import Path

import wordwall
from question_planner import build_question_plan, validate_asset_manifest
from wordwall_catalog import recommend_templates


class WordwallHelpersTest(unittest.TestCase):
    def test_plan_uses_text_for_plain_text_quiz(self):
        plan = build_question_plan("建立純文字質數選擇題")
        self.assertEqual(plan["decision"]["template"], "quiz")
        self.assertEqual(plan["decision"]["asset_level"], "text")
        self.assertEqual(plan["content_contract"]["items"][0]["question"],
                         "文字題幹")

    def test_plan_uses_composite_screenshot_for_geometry_options(self):
        plan = build_question_plan("幾何圖形選擇題，選項也只能用圖片判別")
        self.assertEqual(plan["decision"]["asset_level"], "screenshot")
        self.assertEqual(plan["layout"]["type"],
                         "composite-question-image")

    def test_plan_allows_ai_for_comic_visual_riddle(self):
        plan = build_question_plan(
            "用 AI 生圖製作漫畫解謎選擇題，根據分鏡找出犯人")
        self.assertEqual(plan["decision"]["asset_level"], "ai-image")
        self.assertTrue(plan["ai_novelty_gate"]["passed"])
        self.assertIn("漫畫與連續分鏡",
                      plan["ai_novelty_gate"]["novelty_reasons"])
        self.assertTrue(plan["image_generation"]["required"])
        self.assertEqual(plan["image_generation"]["skill"], "imagegen")
        self.assertEqual(plan["image_generation"]["tool"], "image_gen")
        self.assertIn("不得只輸出 prompt",
                      plan["image_generation"]["unavailable_action"])
        self.assertEqual(
            plan["asset_manifest_contract"]["generation_method"],
            "builtin-imagegen")

    def test_plan_downgrades_ai_for_precise_geometry(self):
        plan = build_question_plan(
            "用 AI 生圖畫精確座標幾何選擇題", requested_level="ai-image")
        self.assertEqual(plan["decision"]["asset_level"], "screenshot")
        self.assertFalse(plan["ai_novelty_gate"]["passed"])
        self.assertEqual(plan["ai_novelty_gate"]["decision"],
                         "downgraded-to-screenshot")

    def test_plan_maps_image_pair_request(self):
        plan = build_question_plan("做一個圖片配圖片的圖形配對遊戲")
        self.assertEqual(plan["decision"]["template"], "match_up")
        self.assertEqual(plan["decision"]["media"], "image-image")
        self.assertEqual(plan["layout"]["type"],
                         "paired-assets-then-capture")

    def test_asset_manifest_validates_composite_screenshot(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            image = base / "question.png"
            image.write_bytes(b"image")
            plan = build_question_plan(
                "幾何圖形選擇題，選項也只能用圖片判別")
            result = validate_asset_manifest({
                "asset_level": "screenshot",
                "generation_method": "existing-or-screenshot",
                "final_assets": [{
                    "role": "composite-question", "path": "question.png"}],
                "capture_finalized": True,
                "math_verified": True,
                "answer_leak_checked": True,
                "mobile_checked": True,
            }, base, plan)
            self.assertEqual(result["asset_count"], 1)

    def test_asset_manifest_requires_prompt_for_ai_level(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            image = base / "question.png"
            image.write_bytes(b"image")
            plan = build_question_plan(
                "用 AI 生圖製作漫畫解謎選擇題")
            manifest = {
                "asset_level": "ai-image",
                "generation_method": "builtin-imagegen",
                "final_assets": [{
                    "role": "composite-question", "path": "question.png"}],
                "capture_finalized": True,
                "math_verified": True,
                "answer_leak_checked": True,
                "mobile_checked": True,
            }
            with self.assertRaisesRegex(ValueError, "prompt"):
                validate_asset_manifest(manifest, base, plan)

    def test_asset_manifest_requires_explicit_imagegen_method(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            image = base / "question.png"
            image.write_bytes(b"image")
            plan = build_question_plan(
                "用 AI 生圖製作漫畫解謎選擇題")
            manifest = {
                "asset_level": "ai-image",
                "generation_method": "chatgpt-subscription",
                "prompt": "四格漫畫解謎題，保持角色一致",
                "final_assets": [{
                    "role": "composite-question", "path": "question.png"}],
                "capture_finalized": True,
                "math_verified": True,
                "answer_leak_checked": True,
                "mobile_checked": True,
            }
            with self.assertRaisesRegex(ValueError, "builtin-imagegen"):
                validate_asset_manifest(manifest, base, plan)

    def test_deadline_format(self):
        self.assertEqual(
            wordwall._deadline_for_wordwall("2026-08-31"), "31/08/2026")

    def test_validate_quiz_with_relative_image(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            image = base / "q1.png"
            image.write_bytes(b"test-image")
            content = {
                "template": "quiz",
                "items": [{
                    "question": "請看圖作答",
                    "image": "q1.png",
                    "answers": ["A", "B", "C", "D"],
                    "correct": 2,
                }],
            }
            paths = wordwall._validate_quiz_content(content, base)
            self.assertEqual(paths, [image.resolve()])

    def test_validate_quiz_rejects_bad_correct_index(self):
        content = {
            "template": "quiz",
            "items": [{
                "question": "題目",
                "answers": ["A", "B"],
                "correct": 2,
            }],
        }
        with self.assertRaisesRegex(ValueError, "correct"):
            wordwall._validate_quiz_content(content, Path.cwd())

    def test_prepare_quiz_supports_image_answers(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            for name in ("question.png", "a.png", "b.png"):
                (base / name).write_bytes(b"image")
            content = {
                "items": [{
                    "question": {"image": "question.png"},
                    "answers": [
                        {"text": "A", "image": "a.png"},
                        {"image": "b.png"},
                    ],
                    "correct": 1,
                }],
            }
            prepared = wordwall._prepare_content(
                content, base, "quiz")
            self.assertEqual(prepared["schema"], "quiz")
            self.assertEqual(prepared["image_count"], 3)
            self.assertEqual(prepared["items"][0]["answers"][1]["text"], "")

    def test_prepare_pair_supports_legacy_and_media_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            image = base / "shape.png"
            image.write_bytes(b"image")
            content = {"pairs": [
                {"keyword": "三角形", "definition": "三邊形"},
                {"left": {"image": "shape.png"}, "right": "圖形名稱"},
                {"left": "A", "right": {"text": "B", "image": "shape.png"}},
            ]}
            prepared = wordwall._prepare_content(
                content, base, "match_up")
            self.assertEqual(prepared["schema"], "pair")
            self.assertEqual(prepared["item_count"], 3)
            self.assertEqual(prepared["image_count"], 2)

    def test_prepare_group_counts_groups_items_and_images(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            image = base / "shape.png"
            image.write_bytes(b"image")
            content = {"groups": [
                {"title": "三角形", "items": [
                    "銳角三角形", {"image": "shape.png"}]},
                {"name": "四邊形", "items": ["正方形"]},
            ]}
            prepared = wordwall._prepare_content(
                content, base, "group_sort")
            self.assertEqual(prepared["schema"], "group")
            self.assertEqual(prepared["group_count"], 2)
            self.assertEqual(prepared["item_count"], 3)
            self.assertEqual(prepared["image_count"], 1)

    def test_prepare_true_false_splits_fixed_groups(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            image = base / "shape.png"
            image.write_bytes(b"image")
            content = {"items": [
                {"statement": "2 是質數", "correct": True},
                {"statement": "9 是質數", "correct": False},
                {"statement": "圖形題", "image": "shape.png",
                 "correct": True},
            ]}
            prepared = wordwall._prepare_content(
                content, base, "true_or_false")
            self.assertEqual(prepared["schema"], "fixed_group")
            self.assertEqual(prepared["group_count"], 2)
            self.assertEqual(prepared["item_count"], 3)
            self.assertEqual(prepared["image_count"], 1)

    def test_prepare_matching_pairs_supports_both_modes(self):
        same = wordwall._prepare_content(
            {"mode": "same", "items": ["A", "B", "C"]},
            Path.cwd(), "matching_pairs")
        different = wordwall._prepare_content(
            {"mode": "different", "pairs": [
                {"left": "A", "right": "1"},
                {"left": "B", "right": "2"},
                {"left": "C", "right": "3"},
            ]}, Path.cwd(), "matching_pairs")
        self.assertEqual((same["schema"], same["editor_mode"]),
                         ("single", 1))
        self.assertEqual((different["schema"], different["editor_mode"]),
                         ("pair", 2))

    def test_prepare_single_rejects_wheel_question_mode(self):
        content = {"mode": "question", "items": ["A", "B", "C"]}
        with self.assertRaisesRegex(ValueError, "簡易模式"):
            wordwall._prepare_content(
                content, Path.cwd(), "spin_the_wheel")

    def test_prepare_single_supports_media_items(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            image = base / "shape.png"
            image.write_bytes(b"image")
            prepared = wordwall._prepare_content({"items": [
                "文字卡", {"text": "圖片卡", "image": "shape.png"},
                "第三張卡",
            ]}, base, "speaking_cards")
            self.assertEqual(prepared["schema"], "single")
            self.assertEqual(prepared["item_count"], 3)
            self.assertEqual(prepared["image_count"], 1)

    def test_parse_cloze_sentence_tracks_answer_position(self):
        visible, gaps = wordwall._parse_cloze_sentence(
            "三角形內角和是{{180度}}。", 1)
        self.assertEqual(visible, "三角形內角和是180度。")
        self.assertEqual(gaps, [{"position": 7, "answer": "180度"}])

    def test_parse_cloze_rejects_multiple_gaps_per_page(self):
        with self.assertRaisesRegex(ValueError, "只支援一個"):
            wordwall._parse_cloze_sentence(
                "{{正方形}}有{{四條}}等長的邊。", 1)

    def test_prepare_cloze_counts_pages_and_image(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            image = base / "shape.png"
            image.write_bytes(b"image")
            content = {"pages": [{
                "sentence": "三角形內角和是{{180度}}。",
                "wrong_answers": ["90度"],
                "image": "shape.png",
            }]}
            prepared = wordwall._prepare_content(
                content, base, "complete_the_sentence")
            self.assertEqual(prepared["schema"], "cloze")
            self.assertEqual(prepared["item_count"], 1)
            self.assertEqual(prepared["image_count"], 1)
            self.assertEqual(prepared["items"][0]["gaps"][0]["answer"],
                             "180度")

    def test_prepare_diagram_validates_image_labels_and_coordinates(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            image = base / "diagram.png"
            image.write_bytes(b"image")
            content = {
                "image": "diagram.png",
                "labels": [
                    {"text": "A", "x": 0.1, "y": 0.2},
                    {"text": "B", "x": 0.5, "y": 0.5},
                    {"text": "C", "x": 0.9, "y": 0.8},
                ],
            }
            prepared = wordwall._prepare_content(
                content, base, "labelled_diagram")
            self.assertEqual(prepared["schema"], "diagram")
            self.assertEqual(prepared["item_count"], 3)
            self.assertEqual(prepared["image_count"], 1)
            self.assertEqual(prepared["items"][1]["x"], 0.5)

    def test_prepare_diagram_rejects_out_of_range_coordinates(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            image = base / "diagram.png"
            image.write_bytes(b"image")
            content = {"image": "diagram.png", "labels": [
                {"text": "A", "x": -0.1, "y": 0.2},
                {"text": "B", "x": 0.5, "y": 0.5},
                {"text": "C", "x": 0.9, "y": 0.8},
            ]}
            with self.assertRaisesRegex(ValueError, "0 到 1"):
                wordwall._prepare_content(
                    content, base, "labelled_diagram")

    def test_recommend_image_pairs_returns_implemented_pair_templates(self):
        rows = recommend_templates(
            schema="pair", media="image-image", implemented_only=True)
        names = {row["template"] for row in rows}
        self.assertIn("match_up", names)
        self.assertIn("flash_cards", names)
        self.assertTrue(all(row["implemented"] for row in rows))

    def test_unimplemented_template_has_clear_error(self):
        with self.assertRaisesRegex(NotImplementedError, "尚未實作"):
            wordwall._prepare_content(
                {"items": ["A", "B", "C"]}, Path.cwd(),
                "crossword")

    def test_find_result_by_id_and_title(self):
        rows = [
            {"assignment_id": "12", "title": "八年級測驗", "index": 0},
            {"assignment_id": "34", "title": "圖片題實測", "index": 1},
        ]
        self.assertEqual(
            wordwall._find_result_row(rows, "34", None)["index"], 1)
        self.assertEqual(
            wordwall._find_result_row(rows, None, "圖片題")["assignment_id"],
            "34")

    def test_parse_crop_box(self):
        self.assertEqual(
            wordwall._parse_crop_box("55,75,540,215"),
            (55.0, 75.0, 540.0, 215.0))
        self.assertIsNone(wordwall._parse_crop_box(None))

    def test_parse_crop_box_rejects_invalid_values(self):
        with self.assertRaisesRegex(ValueError, "--crop"):
            wordwall._parse_crop_box("10,20,5,30")
        with self.assertRaisesRegex(ValueError, "--crop"):
            wordwall._parse_crop_box("10,20,30")


if __name__ == "__main__":
    unittest.main()
