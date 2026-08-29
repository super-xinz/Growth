#!/usr/bin/env python3
"""Build the 80 x 200 cm GrowthAgent exhibition roll-up poster."""

from __future__ import annotations

import subprocess
from io import BytesIO
from pathlib import Path

from PIL import Image
from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

from generate_growthagent_poster import (
    BODY,
    INK,
    RED_RGB,
    draw_logo,
    draw_qr,
    image_reader_with_crop,
    register_fonts,
    rounded_image,
    tracked_text,
)


ROOT = Path(__file__).resolve().parents[1]
BACKGROUND = ROOT / "assets" / "poster" / "growthagent-expo-background-v3.png"
MAIN_SCREEN = ROOT / "产品截图" / "截屏2026-07-15 03.44.05.png"
SECONDARY_SCREEN = ROOT / "产品截图" / "截屏2026-07-15 03.43.12.png"

PDF_OUT = ROOT / "output" / "pdf" / "GrowthAgent_80x200cm_Expo_v13.pdf"
PNG_OUT = ROOT / "output" / "poster" / "GrowthAgent_80x200cm_Expo_v13_150dpi.png"
PREVIEW_OUT = ROOT / "output" / "poster" / "GrowthAgent_80x200cm_Expo_v13_preview.png"
RENDER_PREFIX = ROOT / "output" / "poster" / ".growthagent-expo-v13-render"

PAGE_W = 800 * mm
PAGE_H = 2000 * mm
LEFT = 58 * mm
RIGHT = PAGE_W - 58 * mm
PRODUCT_URL = "https://growthagent-guikesong.zeabur.app/"

DEEP_GRAPHITE = HexColor("#121212")

# Remove the black screenshot margin and browser chrome while preserving the UI.
SCREEN_CROP = (90, 145, 2250, 1548)


def draw_bold_text(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    font: str,
    size: float,
    color,
    stroke_width: float,
) -> None:
    """Embolden an existing face without changing its measured width."""
    c.saveState()
    c.setFillColor(color)
    c.setStrokeColor(color)
    c.setLineWidth(stroke_width)
    text_object = c.beginText(x, y)
    text_object.setFont(font, size)
    text_object.setFillColor(color)
    text_object.setTextRenderMode(2)
    text_object.textLine(text)
    c.drawText(text_object)
    c.restoreState()


def draw_header(c: canvas.Canvas) -> None:
    logo_y = 1890 * mm
    logo_size = 60 * mm
    draw_logo(c, LEFT, logo_y, logo_size)

    wordmark_size = 40 * mm
    ascent, descent = pdfmetrics.getAscentDescent("HelveticaNeue", wordmark_size)
    wordmark_y = logo_y + (logo_size - (ascent - descent)) / 2 - descent
    c.setFillColor(INK)
    c.setFont("HelveticaNeue", wordmark_size)
    # Align the wordmark's typographic top and bottom with the logo.
    c.drawString(LEFT + 80 * mm, wordmark_y, "GrowthAgent")

    # Balance the brand with one clear product-category statement.
    ai_size = 21 * mm
    cn_size = 18.5 * mm
    gap = 8 * mm
    ai_width = pdfmetrics.stringWidth("AI", "HelveticaNeue", ai_size)
    cn_width = pdfmetrics.stringWidth("全自动获客", "HeitiSC-Medium", cn_size)
    category_x = RIGHT - ai_width - gap - cn_width
    draw_bold_text(
        c,
        "AI",
        category_x,
        1926 * mm,
        "HelveticaNeue",
        ai_size,
        RED_RGB,
        0.48 * mm,
    )
    draw_bold_text(
        c,
        "全自动获客",
        category_x + ai_width + gap,
        1926 * mm,
        "HeitiSC-Medium",
        cn_size,
        INK,
        0.42 * mm,
    )
    c.setFillColor(BODY)
    c.setFont("HeitiSC-Light", 11.3 * mm)
    c.drawRightString(RIGHT, 1900 * mm, "从读懂产品到发现商机与自动触达")


def draw_screenshot_layer(
    c: canvas.Canvas,
    image,
    *,
    x: float,
    y: float,
    width: float,
    angle: float,
    emphasis: bool,
) -> tuple[float, float]:
    crop_w = SCREEN_CROP[2] - SCREEN_CROP[0]
    crop_h = SCREEN_CROP[3] - SCREEN_CROP[1]
    height = width * crop_h / crop_w
    radius = 13 * mm if emphasis else 11 * mm
    frame = 7 * mm if emphasis else 6 * mm

    c.saveState()
    c.translate(x, y)
    c.rotate(angle)

    # A layered, print-safe shadow gives depth without making the UI feel glossy.
    c.saveState()
    c.setFillAlpha(0.10 if emphasis else 0.08)
    c.setFillColor(HexColor("#000000"))
    c.roundRect(8 * mm, -12 * mm, width, height, radius, stroke=0, fill=1)
    c.restoreState()
    c.saveState()
    c.setFillAlpha(0.06)
    c.setFillColor(HexColor("#000000"))
    c.roundRect(3 * mm, -5 * mm, width, height, radius, stroke=0, fill=1)
    c.restoreState()

    c.setFillColor(white)
    c.roundRect(-frame, -frame, width + 2 * frame, height + 2 * frame, radius + frame, stroke=0, fill=1)
    rounded_image(c, image, 0, 0, width, height, radius)
    c.setStrokeColor(HexColor("#C9C3BC"))
    c.setLineWidth(0.55 * mm)
    c.roundRect(0, 0, width, height, radius, stroke=1, fill=0)
    c.restoreState()
    return width, height


def prepared_background_with_black_fade(path: Path) -> ImageReader:
    """Fuse a seamless warm-background-to-graphite fade into the source pixels."""
    with Image.open(path) as source:
        background = source.convert("RGB").resize((3172, 7932), Image.Resampling.LANCZOS)
        width, height = background.size
        fade_start = round(height * (1 - 870 / 2000))
        solid_start = round(height * (1 - 700 / 2000))
        mask_values: list[int] = []
        for row in range(height):
            if row <= fade_start:
                alpha = 0
            elif row >= solid_start:
                alpha = 255
            else:
                progress = (row - fade_start) / (solid_start - fade_start)
                smooth = progress * progress * (3 - 2 * progress)
                alpha = round(255 * smooth)
            mask_values.append(alpha)

        mask_column = Image.new("L", (1, height))
        mask_column.putdata(mask_values)
        mask = mask_column.resize((width, height), Image.Resampling.NEAREST)
        graphite = Image.new("RGB", background.size, (18, 18, 18))
        blended = Image.composite(graphite, background, mask)
        buffer = BytesIO()
        blended.save(buffer, format="JPEG", quality=95, subsampling=0, progressive=True)
    buffer.seek(0)
    return ImageReader(buffer)


def feature_block(
    c: canvas.Canvas,
    *,
    number: str,
    title: str,
    body_1: str,
    body_2: str,
    x: float,
    y: float,
    width: float,
) -> None:
    tracked_text(c, number, x, y + 8 * mm, "HelveticaNeue", 12 * mm, RED_RGB, 0.66 * mm)
    c.setFillColor(white)
    c.setFont("HeitiSC-Medium", 24 * mm)
    c.drawString(x + 44 * mm, y, title)
    c.setFillColor(Color(1, 1, 1, alpha=0.70))
    c.setFont("HeitiSC-Light", 16.5 * mm)
    c.drawString(x + 44 * mm, y - 50 * mm, body_1)
    if body_2:
        c.drawString(x + 44 * mm, y - 90 * mm, body_2)
    c.setStrokeColor(Color(1, 1, 1, alpha=0.15))
    c.setLineWidth(0.5 * mm)
    c.line(x, y - 128 * mm, x + width, y - 128 * mm)


def build_pdf() -> None:
    register_fonts()
    PDF_OUT.parent.mkdir(parents=True, exist_ok=True)
    PNG_OUT.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(PDF_OUT), pagesize=(PAGE_W, PAGE_H), pageCompression=1)
    c.setTitle("GrowthAgent 80 x 200 cm Exhibition Roll-up")
    c.setAuthor("GrowthAgent")
    c.setSubject("AI customer-acquisition workbench exhibition poster")

    c.drawImage(prepared_background_with_black_fade(BACKGROUND), 0, 0, width=PAGE_W, height=PAGE_H)

    draw_header(c)

    # Keep the V11 two-line composition, with stronger typographic weight only.
    slogan_size = 45 * mm
    draw_bold_text(
        c,
        "Cursor 为开发做了什么，",
        LEFT,
        1734 * mm,
        "HeitiSC-Medium",
        slogan_size,
        INK,
        0.78 * mm,
    )
    growth_size = 53 * mm
    draw_bold_text(
        c,
        "GrowthAgent",
        LEFT,
        1622 * mm,
        "HelveticaNeue",
        growth_size,
        RED_RGB,
        0.86 * mm,
    )
    growth_width = pdfmetrics.stringWidth("GrowthAgent", "HelveticaNeue", growth_size)
    draw_bold_text(
        c,
        "就为获客做什么。",
        LEFT + growth_width + 7 * mm,
        1622 * mm,
        "HeitiSC-Medium",
        slogan_size,
        INK,
        0.78 * mm,
    )

    main = image_reader_with_crop(MAIN_SCREEN, SCREEN_CROP)
    secondary = image_reader_with_crop(SECONDARY_SCREEN, SCREEN_CROP)
    draw_screenshot_layer(
        c,
        secondary,
        x=150 * mm,
        y=1110 * mm,
        width=560 * mm,
        angle=2.0,
        emphasis=False,
    )
    draw_screenshot_layer(
        c,
        main,
        x=52 * mm,
        y=870 * mm,
        width=670 * mm,
        angle=-0.7,
        emphasis=True,
    )

    # The black information zone is already fused into the background pixels.
    c.setFillColor(white)
    c.setFont("HeitiSC-Medium", 38 * mm)
    c.drawString(LEFT, 666 * mm, "让每个 Vibe Coder，")
    c.drawString(LEFT, 606 * mm, "都为自己的产品找到第一批用户。")
    c.setFillColor(RED_RGB)
    c.setFont("HeitiSC-Medium", 17 * mm)
    c.drawString(LEFT, 544 * mm, "读懂产品  ·  发现需求  ·  判断机会  ·  安全触达")

    c.setStrokeColor(Color(1, 1, 1, alpha=0.18))
    c.setLineWidth(0.55 * mm)
    c.line(LEFT, 505 * mm, RIGHT, 505 * mm)

    feature_block(
        c,
        number="01",
        title="产品大脑",
        body_1="读懂定位、受众与核心卖点",
        body_2="形成带来源证据的产品大脑",
        x=LEFT,
        y=432 * mm,
        width=316 * mm,
    )
    feature_block(
        c,
        number="02",
        title="需求发现",
        body_1="发现求推荐、找替代的信号",
        body_2="优先定位正在表达需求的用户",
        x=423 * mm,
        y=432 * mm,
        width=319 * mm,
    )
    feature_block(
        c,
        number="03",
        title="机会判断",
        body_1="同时计算匹配度、风险与证据",
        body_2="把最值得行动的机会排在前面",
        x=LEFT,
        y=275 * mm,
        width=316 * mm,
    )
    feature_block(
        c,
        number="04",
        title="安全触达",
        body_1="频率、冷却与每日上限可控",
        body_2="触达克制，并且可以随时停止",
        x=423 * mm,
        y=275 * mm,
        width=319 * mm,
    )

    c.setStrokeColor(Color(1, 1, 1, alpha=0.18))
    c.setLineWidth(0.5 * mm)
    c.line(LEFT, 130 * mm, RIGHT, 130 * mm)
    c.setFillColor(white)
    c.setFont("HeitiSC-Medium", 19 * mm)
    c.drawString(LEFT, 90 * mm, "本地优先 · 可自托管 · 开源")
    c.setFillColor(Color(1, 1, 1, alpha=0.58))
    c.setFont("HeitiSC-Light", 12.5 * mm)
    c.drawString(LEFT, 49 * mm, "专为 Vibe Coder 与独立开发者打造")

    qr_size = 125 * mm
    qr_x = RIGHT - qr_size
    qr_y = 18 * mm
    c.setFillColor(white)
    c.roundRect(qr_x, qr_y, qr_size, qr_size, 7 * mm, stroke=0, fill=1)
    draw_qr(c, PRODUCT_URL, qr_x + 9 * mm, qr_y + 9 * mm, qr_size - 18 * mm)
    c.setFillColor(Color(1, 1, 1, alpha=0.72))
    c.setFont("HeitiSC-Medium", 16 * mm)
    c.drawRightString(qr_x - 18 * mm, 66 * mm, "扫码获取项目")

    c.showPage()
    c.save()


def render_pngs() -> None:
    subprocess.run(
        [
            "pdftoppm",
            "-png",
            "-r",
            "150",
            "-singlefile",
            str(PDF_OUT),
            str(RENDER_PREFIX),
        ],
        check=True,
    )
    rendered = RENDER_PREFIX.with_suffix(".png")
    with Image.open(rendered) as source:
        final = source.convert("RGB")
        final.save(PNG_OUT, format="PNG", dpi=(150, 150), compress_level=6)
        preview_w = 1418
        preview_h = round(final.height * preview_w / final.width)
        preview = final.resize((preview_w, preview_h), Image.Resampling.LANCZOS)
        preview.save(PREVIEW_OUT, format="PNG", compress_level=7)
    rendered.unlink(missing_ok=True)


def main() -> None:
    build_pdf()
    render_pngs()
    print(PDF_OUT)
    print(PNG_OUT)
    print(PREVIEW_OUT)


if __name__ == "__main__":
    main()
