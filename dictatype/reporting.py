from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _escape_text(value: Any) -> str:
    """Escape user text for ReportLab Paragraph markup while preserving line breaks."""
    text = html.escape(str(value or ""))
    return text.replace("\n", "<br/>")


def _display_date(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "-"
    # SQLite stores an ISO-like UTC timestamp. Keep this deliberately tolerant.
    return text.replace("T", " ").replace("+00:00", " UTC").replace("Z", " UTC")


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#DCE3F0"))
    canvas.line(18 * mm, 13 * mm, A4[0] - 18 * mm, 13 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#68758F"))
    canvas.drawString(18 * mm, 8 * mm, "DictaType assessment analysis")
    canvas.drawRightString(A4[0] - 18 * mm, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def save_attempt_pdf(
    attempt: dict[str, Any],
    path: str | Path,
    teacher_comment: str = "",
) -> Path:
    """Create a printable PDF analysis for a DictaType attempt."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=19 * mm,
        title="DictaType Assessment Analysis",
        author="DictaType",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DictaTypeTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=21,
        leading=25,
        textColor=colors.HexColor("#18345F"),
        spaceAfter=5,
    )
    subtitle_style = ParagraphStyle(
        "DictaTypeSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#68758F"),
        spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "DictaTypeSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12.5,
        leading=16,
        textColor=colors.HexColor("#18345F"),
        spaceBefore=10,
        spaceAfter=7,
    )
    body_style = ParagraphStyle(
        "DictaTypeBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#1E2943"),
    )
    small_style = ParagraphStyle(
        "DictaTypeSmall",
        parent=body_style,
        fontSize=8.5,
        leading=12,
    )
    header_style = ParagraphStyle(
        "DictaTypeTableHeader",
        parent=small_style,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )
    score_style = ParagraphStyle(
        "DictaTypeScore",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#18345F"),
    )

    details = attempt.get("details", {})
    if not isinstance(details, dict):
        details = {}
    changes = details.get("changes", [])
    if not isinstance(changes, list):
        changes = []

    story = [
        Paragraph("DictaType Assessment Analysis", title_style),
        Paragraph(
            f"Generated result for <b>{_escape_text(attempt.get('student_name', 'Student'))}</b>",
            subtitle_style,
        ),
    ]

    identity_rows = [
        ["Student", _escape_text(attempt.get("student_name", "")), "Class", _escape_text(attempt.get("class_name", "")) or "-"],
        ["Dictation", _escape_text(attempt.get("lesson_title", "")), "Date", _escape_text(_display_date(attempt.get("created_at")))],
        ["Source", _escape_text(attempt.get("source", "desktop")), "Marking mode", _escape_text(details.get("mode", "balanced")).title()],
    ]
    identity_table = Table(
        [[Paragraph(str(cell), small_style) for cell in row] for row in identity_rows],
        colWidths=[25 * mm, 57 * mm, 29 * mm, 51 * mm],
    )
    identity_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF3FA")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#EEF3FA")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#53627D")),
                ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#53627D")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE3F0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([identity_table, Spacer(1, 10)])

    metric_data = [
        [
            Paragraph("Overall", small_style),
            Paragraph("Word accuracy", small_style),
            Paragraph("Character accuracy", small_style),
            Paragraph("Speed", small_style),
            Paragraph("Time", small_style),
            Paragraph("Replays", small_style),
        ],
        [
            Paragraph(f"{float(attempt.get('overall_score', 0)):.1f}%", score_style),
            Paragraph(f"{float(attempt.get('score_word', 0)):.1f}%", score_style),
            Paragraph(f"{float(attempt.get('score_char', 0)):.1f}%", score_style),
            Paragraph(f"{float(attempt.get('wpm', 0)):.1f} WPM", score_style),
            Paragraph(_escape_text(_format_duration(attempt.get("duration_seconds", 0))), score_style),
            Paragraph(str(attempt.get("replay_count", 0)), score_style),
        ],
    ]
    metric_table = Table(metric_data, colWidths=[27 * mm] * 6)
    metric_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F9FD")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#EEF3FA")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE3F0")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend([metric_table, Spacer(1, 5)])

    analysis_rows = [
        ("Correct words", details.get("correct_words", 0)),
        ("Substitutions", details.get("substitutions", 0)),
        ("Missing words", details.get("missing_words", 0)),
        ("Extra words", details.get("extra_words", 0)),
        ("Accent mistakes", details.get("accent_mistakes", 0)),
        ("Capitalisation mistakes", details.get("capitalization_mistakes", 0)),
        ("Punctuation mistakes", details.get("punctuation_mistakes", 0)),
        ("Expected word count", details.get("expected_word_count", "-")),
        ("Typed word count", details.get("actual_word_count", "-")),
    ]
    analysis_table_data = [
        [
            Paragraph("Measure", header_style),
            Paragraph("Value", header_style),
            Paragraph("Measure", header_style),
            Paragraph("Value", header_style),
        ]
    ]
    for index in range(0, len(analysis_rows), 2):
        left_label, left_value = analysis_rows[index]
        if index + 1 < len(analysis_rows):
            right_label, right_value = analysis_rows[index + 1]
        else:
            right_label, right_value = "", ""
        analysis_table_data.append(
            [
                Paragraph(_escape_text(left_label), body_style),
                Paragraph(_escape_text(left_value), body_style),
                Paragraph(_escape_text(right_label), body_style),
                Paragraph(_escape_text(right_value), body_style),
            ]
        )
    analysis_table = Table(
        analysis_table_data,
        colWidths=[55 * mm, 24 * mm, 59 * mm, 24 * mm],
        repeatRows=1,
    )
    analysis_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#18345F")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FD")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE3F0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([Paragraph("Analysis", section_style), analysis_table])

    story.extend(
        [
            Paragraph("Student answer", section_style),
            Table(
                [[Paragraph(_escape_text(attempt.get("answer", "")) or "<i>No answer recorded.</i>", body_style)]],
                colWidths=[162 * mm],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F9FD")),
                        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#DCE3F0")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 9),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                        ("TOPPADDING", (0, 0), (-1, -1), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                    ]
                ),
            ),
        ]
    )

    story.append(Paragraph("Corrections", section_style))
    corrections_data = [
        [Paragraph("Type", header_style), Paragraph("Expected", header_style), Paragraph("Typed", header_style)]
    ]
    if changes:
        for item in changes:
            if not isinstance(item, dict):
                continue
            corrections_data.append(
                [
                    Paragraph(_escape_text(str(item.get("kind", "change")).title()), body_style),
                    Paragraph(_escape_text(item.get("expected", "")) or "-", body_style),
                    Paragraph(_escape_text(item.get("actual", "")) or "-", body_style),
                ]
            )
    if len(corrections_data) == 1:
        corrections_data.append(
            [Paragraph("No word-level corrections.", body_style), Paragraph("-", body_style), Paragraph("-", body_style)]
        )
    corrections_table = Table(corrections_data, colWidths=[36 * mm, 63 * mm, 63 * mm], repeatRows=1)
    corrections_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#18345F")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FD")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE3F0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(corrections_table)

    comment = teacher_comment.strip() or str(attempt.get("teacher_comment", "")).strip()
    story.append(
        KeepTogether(
            [
                Paragraph("Teacher comment", section_style),
                Table(
                    [[Paragraph(_escape_text(comment) if comment else "<i>No teacher comment.</i>", body_style)]],
                    colWidths=[162 * mm],
                    style=TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF9E8")),
                            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#E6D89B")),
                            ("LEFTPADDING", (0, 0), (-1, -1), 9),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                            ("TOPPADDING", (0, 0), (-1, -1), 9),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                        ]
                    ),
                ),
            ]
        )
    )

    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output


def _format_duration(seconds: Any) -> str:
    try:
        total = max(0, int(seconds))
    except (TypeError, ValueError):
        total = 0
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
