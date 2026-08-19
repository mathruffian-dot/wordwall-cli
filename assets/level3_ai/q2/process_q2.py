from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parent
BASE = ROOT / "base.png"
OUTPUT = ROOT / "question.png"


def draw_lamp(layer: Image.Image, x: int, y: int) -> None:
    """Draw one large, mobile-readable magical lantern at a fixed location."""
    glow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for radius, alpha in ((58, 22), (42, 36), (29, 70)):
        gd.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(255, 209, 74, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(14))
    layer.alpha_composite(glow)

    d = ImageDraw.Draw(layer)
    # Short suspension hook and solid frame.
    d.line((x, y - 46, x, y - 34), fill=(62, 38, 66, 255), width=7)
    d.rounded_rectangle((x - 25, y - 35, x + 25, y + 28), radius=10,
                        fill=(86, 50, 72, 255), outline=(250, 221, 113, 255), width=5)
    d.rounded_rectangle((x - 15, y - 24, x + 15, y + 16), radius=8,
                        fill=(255, 201, 57, 255), outline=(255, 244, 177, 255), width=4)
    d.ellipse((x - 9, y - 18, x + 9, y + 9), fill=(255, 246, 177, 255))
    d.line((x - 30, y + 32, x + 30, y + 32), fill=(54, 34, 65, 255), width=7)


def add_dense_mist(layer: Image.Image, center_x: int) -> None:
    """Opaque foreground mist that completely covers the two lower lamp positions."""
    mist = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(mist)
    # Overlapping ellipses give an unmistakable fog bank with no lamp leakage.
    ellipses = [
        (center_x - 230, 610, center_x + 15, 810),
        (center_x - 110, 575, center_x + 130, 820),
        (center_x + 5, 605, center_x + 245, 815),
        (center_x - 260, 690, center_x + 265, 900),
    ]
    for box in ellipses:
        d.ellipse(box, fill=(155, 192, 255, 252))
    mist = mist.filter(ImageFilter.GaussianBlur(16))
    layer.alpha_composite(mist)
    # Crisp highlights keep the fog readable after Wordwall compression.
    d2 = ImageDraw.Draw(layer)
    d2.arc((center_x - 190, 626, center_x + 45, 775), 205, 342,
           fill=(222, 236, 255, 185), width=10)
    d2.arc((center_x - 25, 615, center_x + 205, 775), 198, 334,
           fill=(216, 232, 255, 170), width=9)


def main() -> None:
    image = Image.open(BASE).convert("RGBA")
    # Centers measured from the generated, front-facing three-arch composition.
    centers = (330, 835, 1340)
    x_offsets = (-72, 72)
    y_rows = (515, 680)

    # Draw the full mathematical structure first: four lamps in every arch.
    for center_x in centers:
        for dx in x_offsets:
            for y in y_rows:
                draw_lamp(image, center_x + dx, y)

    # Only the lower two lamps of arches 2 and 3 are hidden by deterministic fog.
    add_dense_mist(image, centers[1])
    add_dense_mist(image, centers[2])

    image.convert("RGB").save(OUTPUT, quality=95)
    print(f"saved={OUTPUT}")
    print(f"size={image.width}x{image.height}")
    print("visible_lamps=8 hidden_lamps=4")


if __name__ == "__main__":
    main()
