#!/usr/bin/env python3
"""Generate three minimal 80 x 200 cm GrowthAgent poster concepts."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from generate_growthagent_poster import (
    GRAPHITE,
    INK,
    RED_RGB,
    WARM_WHITE,
    draw_logo,
    draw_qr,
    prepared_background,
    register_fonts,
    tracked_text,
)


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "poster" / "concepts"
OUT = ROOT / "output" / "pdf" / "concepts"
PAGE_W = 800 * mm
PAGE_H = 2000 * mm
LEFT = 58 * mm
RIGHT = PAGE_W - 58 * mm
GITHUB = "https://github.com/super-xinz/ThreadPilot"


def header(c: canvas.Canvas, *, light: bool) -> None:
    ink = white if light else INK
    muted = Color(1, 1, 1, alpha=0.60) if light else HexColor("#5B5B5B")
    line = Color(1, 1, 1, alpha=0.24) if light else Color(0, 0, 0, alpha=0.16)
    draw_logo(c, LEFT, 1908 * mm, 39 * mm)
    c.setFillColor(ink)
    c.setFont("HelveticaNeue", 13.7 * mm)
    c.drawString(LEFT + 54 * mm, 1931 * mm, "GrowthAgent")
    tracked_text(
        c,
        "AI CUSTOMER ACQUISITION WORKBENCH",
        475 * mm,
        1931 * mm,
        "HelveticaNeue",
        5.0 * mm,
        muted,
        0.55 * mm,
    )
    c.setStrokeColor(line)
    c.setLineWidth(0.5 * mm)
    c.line(LEFT, 1871 * mm, RIGHT, 1871 * mm)


def footer(
    c: canvas.Canvas,
    *,
    light: bool,
    qr_x: float = 665 * mm,
    qr_y: float = 112 * mm,
    align_right: bool = False,
) -> None:
    ink = white if light else INK
    muted = Color(1, 1, 1, alpha=0.68) if light else HexColor("#5C5C5C")
    box = white if light else WARM_WHITE
    c.setFillColor(ink)
    c.setFont("HeitiSC-Medium", 7.1 * mm)
    footer_text = "本地优先  /  可自托管  /  开源"
    if align_right:
        c.drawRightString(RIGHT, 173 * mm, footer_text)
        c.setFillColor(muted)
        c.setFont("HelveticaNeue", 5.4 * mm)
        c.drawRightString(RIGHT, 148 * mm, "github.com/super-xinz/ThreadPilot")
    else:
        c.drawString(LEFT, 173 * mm, footer_text)
        c.setFillColor(muted)
        c.setFont("HelveticaNeue", 5.4 * mm)
        c.drawString(LEFT, 148 * mm, "github.com/super-xinz/ThreadPilot")

    c.setFillColor(box)
    c.roundRect(qr_x, qr_y, 82 * mm, 82 * mm, 7 * mm, stroke=0, fill=1)
    draw_qr(c, GITHUB, qr_x + 8 * mm, qr_y + 8 * mm, 66 * mm)


def flow(c: canvas.Canvas, y: float, *, light: bool, compact: bool = False) -> None:
    ink = white if light else INK
    muted = Color(1, 1, 1, alpha=0.48) if light else HexColor("#777777")
    items = ("理解产品", "发现需求", "判断机会", "克制触达")
    positions = (LEFT, 233 * mm, 408 * mm, 583 * mm) if not compact else (LEFT, 205 * mm, 352 * mm, 499 * mm)
    for idx, (item, x) in enumerate(zip(items, positions)):
        tracked_text(c, f"0{idx + 1}", x, y + 25 * mm, "HelveticaNeue", 5.2 * mm, RED_RGB, 0.45 * mm)
        c.setFillColor(ink)
        c.setFont("HeitiSC-Medium", 10.1 * mm)
        c.drawString(x, y, item)
        if idx < 3:
            c.setStrokeColor(muted)
            c.setLineWidth(0.45 * mm)
            end_x = positions[idx + 1] - 25 * mm
            c.line(x, y - 17 * mm, end_x, y - 17 * mm)


def base_canvas(path: Path, title: str) -> canvas.Canvas:
    c = canvas.Canvas(str(path), pagesize=(PAGE_W, PAGE_H), pageCompression=1)
    c.setTitle(title)
    c.setAuthor("GrowthAgent")
    c.setSubject("GrowthAgent exhibition poster concept")
    return c


def concept_a() -> Path:
    path = OUT / "GrowthAgent_Concept_A_LightPath.pdf"
    c = base_canvas(path, "GrowthAgent Poster Concept A - Light Path")
    c.drawImage(prepared_background(ASSETS / "v2-a-light-path.png"), 0, 0, PAGE_W, PAGE_H)
    c.saveState()
    c.setFillAlpha(0.22)
    c.setFillColor(WARM_WHITE)
    c.rect(0, 1050 * mm, PAGE_W, 950 * mm, stroke=0, fill=1)
    c.restoreState()
    header(c, light=False)

    tracked_text(c, "THE GROWTH WORKBENCH", LEFT, 1808 * mm, "HelveticaNeue", 6.2 * mm, RED_RGB, 0.75 * mm)
    c.setFillColor(INK)
    c.setFont("SongtiSC-Bold", 43 * mm)
    c.drawString(LEFT, 1685 * mm, "Cursor 为开发做了什么，")
    c.setFillColor(RED_RGB)
    c.setFont("HelveticaNeue", 66 * mm)
    c.drawString(LEFT, 1515 * mm, "GrowthAgent")
    c.setFillColor(INK)
    c.setFont("SongtiSC-Bold", 48 * mm)
    c.drawString(LEFT, 1380 * mm, "就为获客做什么。")

    c.setFillColor(HexColor("#4F4D4A"))
    c.setFont("HeitiSC-Light", 10.2 * mm)
    c.drawString(LEFT, 1285 * mm, "让每个好产品，都能找到它的第一批用户。")

    flow(c, 310 * mm, light=True)
    footer(c, light=True)
    c.showPage()
    c.save()
    return path


def concept_b() -> Path:
    path = OUT / "GrowthAgent_Concept_B_FocusSignal.pdf"
    c = base_canvas(path, "GrowthAgent Poster Concept B - Focus Signal")
    c.drawImage(prepared_background(ASSETS / "v2-b-focus-signal.png"), 0, 0, PAGE_W, PAGE_H)
    c.saveState()
    c.setFillAlpha(0.12)
    c.setFillColor(GRAPHITE)
    c.rect(0, 980 * mm, PAGE_W, 1020 * mm, stroke=0, fill=1)
    c.restoreState()
    header(c, light=True)

    tracked_text(c, "ONE REAL NEED. ONE CLEAR OPPORTUNITY.", LEFT, 1804 * mm, "HelveticaNeue", 5.7 * mm, RED_RGB, 0.58 * mm)
    c.setFillColor(white)
    c.setFont("HeitiSC-Medium", 48 * mm)
    c.drawString(LEFT, 1675 * mm, "Cursor 为开发")
    c.drawString(LEFT, 1557 * mm, "做了什么，")
    c.setFillColor(RED_RGB)
    c.setFont("HelveticaNeue", 61 * mm)
    c.drawString(LEFT, 1408 * mm, "GrowthAgent")
    c.setFillColor(white)
    c.setFont("HeitiSC-Medium", 46 * mm)
    c.drawString(LEFT, 1288 * mm, "就为获客做什么。")

    c.setFillColor(Color(1, 1, 1, alpha=0.68))
    c.setFont("HeitiSC-Light", 9.5 * mm)
    c.drawString(LEFT, 1205 * mm, "从真实需求中，找到值得触达的那一个。")

    flow(c, 310 * mm, light=True)
    footer(c, light=True)
    c.showPage()
    c.save()
    return path


def concept_c() -> Path:
    path = OUT / "GrowthAgent_Concept_C_RedChannel.pdf"
    c = base_canvas(path, "GrowthAgent Poster Concept C - Red Channel")
    c.drawImage(prepared_background(ASSETS / "v2-c-red-channel.png"), 0, 0, PAGE_W, PAGE_H)
    header(c, light=False)

    tracked_text(c, "FROM BUILDING TO GROWTH", LEFT, 1807 * mm, "HelveticaNeue", 6.0 * mm, RED_RGB, 0.72 * mm)
    c.setFillColor(INK)
    c.setFont("HeitiSC-Medium", 39 * mm)
    c.drawString(LEFT, 1690 * mm, "Cursor 为开发")
    c.drawString(LEFT, 1590 * mm, "做了什么，")
    c.setFillColor(RED_RGB)
    c.setFont("HelveticaNeue", 58 * mm)
    c.drawString(LEFT, 1446 * mm, "GrowthAgent")
    c.setFillColor(INK)
    c.setFont("HeitiSC-Medium", 38 * mm)
    c.drawString(LEFT, 1342 * mm, "就为获客做什么。")

    c.setFillColor(HexColor("#52504D"))
    c.setFont("HeitiSC-Light", 9.3 * mm)
    c.drawString(LEFT, 1252 * mm, "让每个好产品，都能找到它的第一批用户。")

    # Preserve the lower visual as a single uninterrupted red gesture.
    footer(c, light=True, qr_x=LEFT, qr_y=112 * mm, align_right=True)
    c.showPage()
    c.save()
    return path


def main() -> None:
    register_fonts()
    OUT.mkdir(parents=True, exist_ok=True)
    for generated in (concept_a(), concept_b(), concept_c()):
        print(generated)


if __name__ == "__main__":
    main()
