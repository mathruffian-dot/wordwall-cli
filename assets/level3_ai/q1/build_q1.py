from pathlib import Path
import json

from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parent
BASE = Image.open(ROOT / "base.png").convert("RGB")
SIDE = 768


def fitted(image: Image.Image) -> Image.Image:
    return ImageOps.fit(image, (SIDE, SIDE), method=Image.Resampling.LANCZOS)


zero = fitted(BASE)
ninety = zero.transpose(Image.Transpose.ROTATE_90)
one_eighty = zero.transpose(Image.Transpose.ROTATE_180)
two_seventy = zero.transpose(Image.Transpose.ROTATE_270)
mirror = ImageOps.mirror(zero)

# A is deliberately the correct continuation. The other files are controlled
# distractors built from the exact same source scene.
options = [two_seventy, mirror, zero, one_eighty]
for letter, image in zip("abcd", options):
    image.save(ROOT / f"option_{letter}.png", optimize=True)

# Three large panels in reading order. The neutral gutters and arrowheads are
# post-processing UI, not text baked into the AI artwork.
pad = 32
gap = 76
panel = 720
canvas_w = pad * 2 + panel * 3 + gap * 2
canvas_h = pad * 2 + panel
canvas = Image.new("RGB", (canvas_w, canvas_h), "#EEE9DC")
draw = ImageDraw.Draw(canvas)

for idx, image in enumerate((zero, ninety, one_eighty)):
    x = pad + idx * (panel + gap)
    y = pad
    tile = image.resize((panel, panel), Image.Resampling.LANCZOS)
    canvas.paste(tile, (x, y))
    draw.rounded_rectangle((x - 3, y - 3, x + panel + 2, y + panel + 2), radius=16, outline="#3B4553", width=6)

for idx in (0, 1):
    x0 = pad + panel + idx * (panel + gap) + 18
    cy = canvas_h // 2
    draw.line((x0, cy, x0 + 38, cy), fill="#3B4553", width=10)
    draw.polygon(((x0 + 38, cy - 18), (x0 + 38, cy + 18), (x0 + 60, cy)), fill="#3B4553")

canvas.save(ROOT / "question.png", optimize=True)

payload = {
    "id": "level3-ai-q1-rotation",
    "title": "機械密室的旋轉規律",
    "question": "觀察密室依序旋轉的規律，下一張圖片應該是哪一張？",
    "type": "image_options",
    "question_image": "question.png",
    "options": [
        {"label": "A", "image": "option_a.png"},
        {"label": "B", "image": "option_b.png"},
        {"label": "C", "image": "option_c.png"},
        {"label": "D", "image": "option_d.png"},
    ],
    "correct_index": 0,
    "correct_label": "A",
    "explanation": "每次逆時針旋轉九十度，因此下一張是原圖逆時針旋轉二百七十度。",
    "source_image": "base.png",
    "generation_level": 3,
}
(ROOT / "question.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

