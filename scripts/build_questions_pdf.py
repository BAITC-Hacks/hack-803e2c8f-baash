"""Render the maintained RU/EN GovTech question list into a shareable PDF."""

from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "GOVTECH_BUSINESS_QUESTIONS.md"
OUTPUT = ROOT / "output" / "pdf" / "govtech_business_questions.pdf"


def font_path(bold: bool) -> Path:
    candidates = (
        [
            Path("C:/Windows/Fonts/arialbd.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ]
        if bold
        else [
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ]
    )
    return next((path for path in candidates if path.is_file()), candidates[0])


def footer(canvas: object, doc: BaseDocTemplate) -> None:
    page = canvas  # type: ignore[assignment]
    page.saveState()
    page.setFont("GovTech", 8)
    page.setFillColor(colors.HexColor("#65706d"))
    page.drawString(44, 28, "Pulse 109 | GovTech organizer questions | synthetic demo context")
    page.drawRightString(A4[0] - 44, 28, str(doc.page))
    page.restoreState()


def main() -> None:
    pdfmetrics.registerFont(TTFont("GovTech", str(font_path(False))))
    pdfmetrics.registerFont(TTFont("GovTech-Bold", str(font_path(True))))
    pdfmetrics.registerFontFamily("GovTech", normal="GovTech", bold="GovTech-Bold")
    normal = ParagraphStyle(
        "normal",
        fontName="GovTech",
        fontSize=10.2,
        leading=15.5,
        textColor=colors.HexColor("#18201f"),
        spaceAfter=11,
    )
    title = ParagraphStyle(
        "title",
        parent=normal,
        fontName="GovTech-Bold",
        fontSize=17,
        leading=22,
        alignment=TA_CENTER,
        spaceAfter=18,
    )
    heading = ParagraphStyle(
        "heading",
        parent=normal,
        fontName="GovTech-Bold",
        fontSize=13,
        leading=18,
        textColor=colors.HexColor("#147d73"),
        spaceBefore=13,
        spaceAfter=11,
        keepWithNext=True,
    )
    question = ParagraphStyle("question", parent=normal, leftIndent=12, firstLineIndent=-12)
    story: list[object] = []
    for raw in SOURCE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("# "):
            story.append(Paragraph(html.escape(line[2:]), title))
            continue
        if line.startswith("## "):
            story.append(Spacer(1, 7))
            story.append(Paragraph(html.escape(line[3:]), heading))
            continue
        escaped = html.escape(line)
        escaped = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", escaped)
        story.append(Paragraph(escaped, question if re.match(r"^\d+\.", line) else normal))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=44,
        rightMargin=44,
        topMargin=44,
        bottomMargin=50,
        title="Pulse 109 GovTech business questions",
        author="Pulse 109",
    )
    frame = Frame(
        44, 50, A4[0] - 88, A4[1] - 94, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0
    )
    doc.addPageTemplates(PageTemplate(id="questions", frames=[frame], onPage=footer))
    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    main()
