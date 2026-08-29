#!/usr/bin/env python3
"""Generate the 80 x 200 cm GrowthAgent exhibition poster."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import CMYKColor, Color, HexColor, white
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "GrowthAgent_80x200cm_poster.pdf"
BACKGROUND = ROOT / "assets" / "poster" / "growth-signal-background.png"
SCREENSHOT = ROOT / "产品截图" / "截屏2026-07-15 03.43.12.png"

PAGE_W = 800 * mm
PAGE_H = 2000 * mm

RED = CMYKColor(0, 1, 1, 0.10)
RED_RGB = HexColor("#E60000")
INK = CMYKColor(0, 0, 0, 0.92)
GRAPHITE = HexColor("#171717")
BODY = HexColor("#575A60")
MUTED = HexColor("#8B8E94")
WARM_WHITE = HexColor("#F7F4F0")
LINE = HexColor("#D8D4CF")


def register_fonts() -> None:
    pdfmetrics.registerFont(
        TTFont(
            "HeitiSC-Light",
            "/System/Library/Fonts/STHeiti Light.ttc",
            subfontIndex=1,
        )
    )
    pdfmetrics.registerFont(
        TTFont(
            "HeitiSC-Medium",
            "/System/Library/Fonts/STHeiti Medium.ttc",
            subfontIndex=1,
        )
    )
    pdfmetrics.registerFont(
        TTFont(
            "SongtiSC-Bold",
            "/System/Library/Fonts/Supplemental/Songti.ttc",
            subfontIndex=1,
        )
    )
    pdfmetrics.registerFont(
        TTFont(
            "SongtiSC-Regular",
            "/System/Library/Fonts/Supplemental/Songti.ttc",
            subfontIndex=6,
        )
    )
    pdfmetrics.registerFont(
        TTFont(
            "HelveticaNeue",
            "/System/Library/Fonts/HelveticaNeue.ttc",
            subfontIndex=0,
        )
    )


def tracked_text(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    font: str,
    size: float,
    color,
    tracking: float = 0,
) -> None:
    t = c.beginText(x, y)
    t.setFont(font, size)
    t.setFillColor(color)
    t.setCharSpace(tracking)
    t.textLine(text)
    c.drawText(t)


def draw_logo(c: canvas.Canvas, x: float, y: float, size: float) -> None:
    radius = size * 0.22
    c.setFillColor(RED_RGB)
    c.roundRect(x, y, size, size, radius, stroke=0, fill=1)
    c.setStrokeColor(white)
    c.setFillColor(white)
    c.setLineWidth(size * 0.055)
    c.setLineCap(1)
    c.setLineJoin(1)

    # Route and arrow geometry are derived from the project's SVG logo.
    sx = size / 32
    c.line(x + 7.5 * sx, y + 10.5 * sx, x + 13 * sx, y + 16 * sx)
    c.line(x + 13 * sx, y + 16 * sx, x + 17.2 * sx, y + 12.8 * sx)
    c.line(x + 17.2 * sx, y + 12.8 * sx, x + 24.5 * sx, y + 22 * sx)
    c.line(x + 19.3 * sx, y + 22 * sx, x + 24.5 * sx, y + 22 * sx)
    c.line(x + 24.5 * sx, y + 22 * sx, x + 24.5 * sx, y + 16.8 * sx)
    for px, py in ((7.5, 10.5), (13, 16), (17.2, 12.8)):
        c.circle(x + px * sx, y + py * sx, 2 * sx, stroke=0, fill=1)


def image_reader_with_crop(path: Path, crop_box: tuple[int, int, int, int]) -> ImageReader:
    with Image.open(path) as im:
        cropped = im.convert("RGB").crop(crop_box)
        cropped = ImageEnhance.Sharpness(cropped).enhance(1.08)
        buf = BytesIO()
        cropped.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return ImageReader(buf)


def prepared_background(path: Path) -> ImageReader:
    with Image.open(path) as im:
        bg = im.convert("RGB")
        # The art is intentionally abstract; a high-quality upsample keeps its
        # low-frequency gradients and red edge smooth in large-format output.
        bg = bg.resize((3172, 7932), Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=0.35))
        buf = BytesIO()
        bg.save(buf, format="JPEG", quality=94, subsampling=0, progressive=True)
    buf.seek(0)
    return ImageReader(buf)


def rounded_image(
    c: canvas.Canvas,
    image: ImageReader,
    x: float,
    y: float,
    width: float,
    height: float,
    radius: float,
) -> None:
    c.saveState()
    path = c.beginPath()
    path.roundRect(x, y, width, height, radius)
    c.clipPath(path, stroke=0, fill=0)
    c.drawImage(image, x, y, width=width, height=height, mask="auto")
    c.restoreState()


def draw_qr(c: canvas.Canvas, data: str, x: float, y: float, size: float) -> None:
    qr = QrCodeWidget(data, barLevel="M")
    x0, y0, x1, y1 = qr.getBounds()
    drawing = Drawing(size, size, transform=[size / (x1 - x0), 0, 0, size / (y1 - y0), 0, 0])
    qr.barFillColor = GRAPHITE
    qr.barStrokeColor = GRAPHITE
    drawing.add(qr)
    renderPDF.draw(drawing, c, x, y)


def feature(
    c: canvas.Canvas,
    number: str,
    title: str,
    body_lines: tuple[str, str],
    x: float,
    y: float,
    width: float,
) -> None:
    tracked_text(c, number, x, y + 7 * mm, "HelveticaNeue", 8.5 * mm, RED_RGB, 0.35 * mm)
    c.setFillColor(white)
    c.setFont("HeitiSC-Medium", 11.2 * mm)
    c.drawString(x + 35 * mm, y + 7 * mm, title)
    c.setFillColor(Color(1, 1, 1, alpha=0.67))
    c.setFont("HeitiSC-Light", 6.7 * mm)
    c.drawString(x + 35 * mm, y - 14 * mm, body_lines[0])
    c.drawString(x + 35 * mm, y - 26 * mm, body_lines[1])
    c.setStrokeColor(Color(1, 1, 1, alpha=0.17))
    c.setLineWidth(0.5 * mm)
    c.line(x, y - 44 * mm, x + width, y - 44 * mm)


def build() -> None:
    register_fonts()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(OUTPUT), pagesize=(PAGE_W, PAGE_H), pageCompression=1)
    c.setTitle("GrowthAgent - 80 x 200 cm Exhibition Poster")
    c.setAuthor("GrowthAgent")
    c.setSubject("Local-first, self-hosted AI customer acquisition workbench")

    # Full-bleed generated material study, used only as a restrained background.
    c.drawImage(prepared_background(BACKGROUND), 0, 0, width=PAGE_W, height=PAGE_H)

    # Lift the editorial white field for clean typography.
    c.saveState()
    c.setFillAlpha(0.91)
    c.setFillColor(WARM_WHITE)
    c.rect(0, 690 * mm, PAGE_W, 1310 * mm, stroke=0, fill=1)
    c.restoreState()

    # Deepen the lower story panel while retaining a hint of the red signal path.
    c.saveState()
    c.setFillAlpha(0.84)
    c.setFillColor(GRAPHITE)
    c.rect(0, 0, PAGE_W, 690 * mm, stroke=0, fill=1)
    c.restoreState()

    left = 58 * mm
    right = PAGE_W - 58 * mm

    # Brand header.
    draw_logo(c, left, 1914 * mm, 36 * mm)
    c.setFillColor(INK)
    c.setFont("HelveticaNeue", 13.2 * mm)
    c.drawString(left + 50 * mm, 1934 * mm, "GrowthAgent")
    c.setFillColor(BODY)
    c.setFont("HeitiSC-Light", 6.1 * mm)
    c.drawString(left + 50 * mm, 1917 * mm, "AI 机会工作台")
    tracked_text(
        c,
        "LOCAL-FIRST / SELF-HOSTED",
        538 * mm,
        1934 * mm,
        "HelveticaNeue",
        5.7 * mm,
        BODY,
        0.55 * mm,
    )
    c.setStrokeColor(LINE)
    c.setLineWidth(0.55 * mm)
    c.line(left, 1884 * mm, right, 1884 * mm)

    # Hero copy.
    tracked_text(
        c,
        "FROM SIGNAL TO GROWTH",
        left,
        1835 * mm,
        "HelveticaNeue",
        6.2 * mm,
        RED_RGB,
        0.9 * mm,
    )
    c.setFillColor(INK)
    c.setFont("SongtiSC-Bold", 48 * mm)
    c.drawString(left, 1716 * mm, "让每个好产品，")
    c.drawString(left, 1603 * mm, "都找到第一批用户。")
    c.setFillColor(BODY)
    c.setFont("HeitiSC-Light", 11.3 * mm)
    c.drawString(left, 1526 * mm, "本地优先、可自托管的 AI 获客工作台")

    c.setFillColor(INK)
    c.setFont("HeitiSC-Medium", 7.9 * mm)
    flow_y = 1471 * mm
    flow_items = ("理解产品", "发现需求", "判断机会", "克制触达")
    flow_x = left
    for index, item in enumerate(flow_items):
        c.drawString(flow_x, flow_y, item)
        flow_x += pdfmetrics.stringWidth(item, "HeitiSC-Medium", 7.9 * mm) + 17 * mm
        if index < len(flow_items) - 1:
            c.setStrokeColor(RED_RGB)
            c.setLineWidth(0.85 * mm)
            c.line(flow_x - 10 * mm, flow_y + 3.2 * mm, flow_x - 3 * mm, flow_y + 3.2 * mm)
            c.setFillColor(INK)

    # Product screenshot with a subtle, print-safe shadow.
    screenshot = image_reader_with_crop(SCREENSHOT, (88, 60, 2252, 1544))
    shot_x = left
    shot_y = 818 * mm
    shot_w = 684 * mm
    shot_h = shot_w * 1484 / 2164
    c.saveState()
    c.setFillAlpha(0.12)
    c.setFillColor(HexColor("#000000"))
    c.roundRect(shot_x + 8 * mm, shot_y - 10 * mm, shot_w, shot_h, 16 * mm, stroke=0, fill=1)
    c.restoreState()
    rounded_image(c, screenshot, shot_x, shot_y, shot_w, shot_h, 14 * mm)
    c.setStrokeColor(HexColor("#BEBAB5"))
    c.setLineWidth(0.6 * mm)
    c.roundRect(shot_x, shot_y, shot_w, shot_h, 14 * mm, stroke=1, fill=0)

    tracked_text(c, "OPPORTUNITY BOARD", left, 765 * mm, "HelveticaNeue", 5.8 * mm, RED_RGB, 0.7 * mm)
    c.setFillColor(BODY)
    c.setFont("HeitiSC-Light", 7.2 * mm)
    c.drawString(left + 121 * mm, 765 * mm, "从原始需求、判断依据到拟回复，在一个界面完成决策。")

    # Lower narrative panel.
    tracked_text(c, "WHY GROWTHAGENT", left, 632 * mm, "HelveticaNeue", 5.8 * mm, RED_RGB, 0.8 * mm)
    c.setFillColor(white)
    c.setFont("SongtiSC-Bold", 27 * mm)
    c.drawString(left, 568 * mm, "把真实需求，变成增长。")
    c.setFillColor(Color(1, 1, 1, alpha=0.70))
    c.setFont("HeitiSC-Light", 7.4 * mm)
    c.drawString(left, 526 * mm, "先理解产品，再发现正在求推荐、寻找替代方案或讨论相关痛点的用户。")
    c.drawString(left, 510 * mm, "每一次触达，都有证据、有判断、有边界。")

    feature(
        c,
        "01",
        "带来源证据的 Product Brain",
        ("从网站或 GitHub 自动梳理定位、受众、", "卖点、能力证据与适用场景。"),
        left,
        438 * mm,
        315 * mm,
    )
    feature(
        c,
        "02",
        "需求驱动的机会发现",
        ("持续发现正在发生的真实需求，", "而不是堆砌泛流量。"),
        423 * mm,
        438 * mm,
        319 * mm,
    )
    feature(
        c,
        "03",
        "匹配与风险双重判断",
        ("用机会分、风险分与可核对依据，", "判断是否值得触达。"),
        left,
        303 * mm,
        315 * mm,
    )
    feature(
        c,
        "04",
        "本地优先的安全边界",
        ("密钥加密、Cookie 本地保存，", "频率、冷却与每日上限全程可控。"),
        423 * mm,
        303 * mm,
        319 * mm,
    )

    # Footer and QR. Critical content stays above the standard roll-up base zone.
    c.setStrokeColor(Color(1, 1, 1, alpha=0.22))
    c.setLineWidth(0.55 * mm)
    c.line(left, 232 * mm, right, 232 * mm)
    tracked_text(c, "OPEN SOURCE / APACHE 2.0", left, 191 * mm, "HelveticaNeue", 5.4 * mm, white, 0.55 * mm)
    c.setFillColor(Color(1, 1, 1, alpha=0.64))
    c.setFont("HeitiSC-Light", 6.7 * mm)
    c.drawString(left, 166 * mm, "产品地址  -  Product Brain  -  需求发现  -  机会判断  -  克制触达")
    c.setFont("HelveticaNeue", 5.8 * mm)
    c.drawString(left, 142 * mm, "github.com/super-xinz/ThreadPilot")

    qr_box = 102 * mm
    qr_x = right - qr_box
    qr_y = 116 * mm
    c.setFillColor(white)
    c.roundRect(qr_x, qr_y, qr_box, qr_box, 8 * mm, stroke=0, fill=1)
    draw_qr(c, "https://github.com/super-xinz/ThreadPilot", qr_x + 10 * mm, qr_y + 10 * mm, 82 * mm)
    c.setFillColor(Color(1, 1, 1, alpha=0.68))
    c.setFont("HeitiSC-Light", 5.5 * mm)
    c.drawRightString(qr_x - 14 * mm, 129 * mm, "扫码查看项目")

    c.showPage()
    c.save()
    print(OUTPUT)


if __name__ == "__main__":
    build()
