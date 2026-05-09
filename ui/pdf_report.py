"""
pdf_report.py — PDF Report Generator for the Recruitment Screening System
Uses reportlab only. No AI involved. Pure data formatting.
"""

from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak,
)


# ── Colour palette ─────────────────────────────────────────────────────────────
C_PRIMARY   = colors.HexColor("#1a3557")   # dark navy
C_ACCENT    = colors.HexColor("#2563eb")   # blue
C_SELECTED  = colors.HexColor("#166534")   # green
C_MODERATE  = colors.HexColor("#92400e")   # amber
C_REJECTED  = colors.HexColor("#991b1b")   # red
C_LIGHT_BG  = colors.HexColor("#f1f5f9")   # very light blue-grey
C_BORDER    = colors.HexColor("#cbd5e1")   # light slate


# ── Style helpers ──────────────────────────────────────────────────────────────
def _styles():
    base = getSampleStyleSheet()
    custom = {
        "Title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontSize=20, textColor=C_PRIMARY,
            spaceAfter=4, leading=24,
        ),
        "Subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontSize=10, textColor=colors.HexColor("#64748b"),
            spaceAfter=2,
        ),
        "SectionHeading": ParagraphStyle(
            "SectionHeading",
            parent=base["Heading2"],
            fontSize=13, textColor=C_PRIMARY,
            spaceBefore=14, spaceAfter=6, leading=16,
            borderPad=4,
        ),
        "SubHeading": ParagraphStyle(
            "SubHeading",
            parent=base["Heading3"],
            fontSize=11, textColor=C_ACCENT,
            spaceBefore=8, spaceAfter=4,
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontSize=9, leading=14, spaceAfter=3,
        ),
        "BulletItem": ParagraphStyle(
            "BulletItem",
            parent=base["Normal"],
            fontSize=9, leading=13, leftIndent=14,
            spaceAfter=2,
        ),
        "TableHeader": ParagraphStyle(
            "TableHeader",
            parent=base["Normal"],
            fontSize=9, textColor=colors.white,
            fontName="Helvetica-Bold",
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            parent=base["Normal"],
            fontSize=9, leading=12,
        ),
    }
    return custom


def _status_color(status: str):
    return {
        "Selected":    C_SELECTED,
        "Moderate Fit": C_MODERATE,
        "Rejected":    C_REJECTED,
    }.get(status, colors.grey)


def _hr():
    return HRFlowable(width="100%", thickness=0.5, color=C_BORDER, spaceAfter=8, spaceBefore=4)


def _bullet(text: str, style) -> Paragraph:
    return Paragraph(f"• {text}", style)


# ══════════════════════════════════════════════════════════════════════════════
# Main generator
# ══════════════════════════════════════════════════════════════════════════════

def generate_pdf_report(jd_details: dict, results: dict) -> bytes:
    """
    Generate a recruitment report PDF.

    Args:
        jd_details: parsed JD dict (department, job_role, skills, experience)
        results:    {filename: {"status": "success"/"error", "data": {...}}}

    Returns:
        PDF file as bytes (ready for st.download_button)
    """
    buf    = BytesIO()
    styles = _styles()
    doc    = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
    )
    story = []

    # ── Separate & sort successful results ────────────────────────────────────
    successful = [
        (fname, r["data"])
        for fname, r in results.items()
        if r.get("status") == "success"
    ]
    successful.sort(key=lambda x: x[1].get("match_percentage", 0), reverse=True)

    total_c    = len(successful)
    selected_c = sum(1 for _, d in successful if d.get("candidate_status") == "Selected")
    moderate_c = sum(1 for _, d in successful if d.get("candidate_status") == "Moderate Fit")
    rejected_c = sum(1 for _, d in successful if d.get("candidate_status") == "Rejected")
    avg_match  = (sum(d.get("match_percentage", 0) for _, d in successful) // total_c
                  if total_c else 0)
    top3 = successful[:3]

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 1 — Title + JD Summary + Recruitment Summary
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Intelligent Recruitment &amp; Workforce Screening System", styles["Title"]))
    story.append(Paragraph("AI-Powered Recruitment Report · Textile &amp; Manufacturing HR", styles["Subtitle"]))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%d %B %Y  %I:%M %p')}", styles["Subtitle"]))
    story.append(Spacer(1, 0.3*cm))
    story.append(_hr())

    # ── Job Description Summary ───────────────────────────────────────────────
    story.append(Paragraph("Job Description Summary", styles["SectionHeading"]))

    jd_data = [
        [Paragraph("Field", styles["TableHeader"]), Paragraph("Details", styles["TableHeader"])],
        ["Department",     jd_details.get("department", "—")],
        ["Job Role",       jd_details.get("job_role", "—")],
        ["Min Experience", f"{jd_details.get('min_work_experience', '?')} years"],
        ["Max Experience", f"{jd_details.get('max_work_experience', '?')} years"],
        ["Required Skills", ", ".join(jd_details.get("skills", [])) or "—"],
    ]
    jd_table = Table(jd_data, colWidths=[4.5*cm, 12*cm])
    jd_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), C_PRIMARY),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 9),
        ("BACKGROUND",   (0, 1), (0, -1), C_LIGHT_BG),
        ("FONTNAME",     (0, 1), (0, -1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID",         (0, 0), (-1, -1), 0.4, C_BORDER),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("PADDING",      (0, 0), (-1, -1), 6),
    ]))
    story.append(jd_table)
    story.append(Spacer(1, 0.4*cm))

    # ── Recruitment Summary ───────────────────────────────────────────────────
    story.append(Paragraph("Recruitment Summary", styles["SectionHeading"]))

    summary_data = [
        [Paragraph("Metric", styles["TableHeader"]), Paragraph("Value", styles["TableHeader"])],
        ["Total Resumes Analyzed",  str(total_c)],
        ["Selected Candidates",     str(selected_c)],
        ["Moderate Fit Candidates", str(moderate_c)],
        ["Rejected Candidates",     str(rejected_c)],
        ["Average Match Percentage", f"{avg_match}%"],
    ]
    s_table = Table(summary_data, colWidths=[8*cm, 8.5*cm])
    s_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), C_PRIMARY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("BACKGROUND",    (0, 1), (0, -1), C_LIGHT_BG),
        ("FONTNAME",      (0, 1), (0, -1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID",          (0, 0), (-1, -1), 0.4, C_BORDER),
        ("PADDING",       (0, 0), (-1, -1), 6),
    ]))
    story.append(s_table)
    story.append(Spacer(1, 0.4*cm))

    # ══════════════════════════════════════════════════════════════════════════
    # Candidate Comparison Table
    # ══════════════════════════════════════════════════════════════════════════
    story.append(_hr())
    story.append(Paragraph("Candidate Comparison Table", styles["SectionHeading"]))

    tbl_header = [
        Paragraph(h, styles["TableHeader"])
        for h in ["#", "Candidate Name", "Department", "Match %", "Status", "Experience"]
    ]
    tbl_data = [tbl_header]
    for rank, (_, d) in enumerate(successful, 1):
        status = d.get("candidate_status", "—")
        status_p = Paragraph(
            f'<font color="{_status_color(status).hexval()}">'
            f'<b>{status}</b></font>',
            styles["TableCell"],
        )
        tbl_data.append([
            str(rank),
            d.get("candidate_name", "—"),
            d.get("department_fit", "—"),
            f"{d.get('match_percentage', '?')}%",
            status_p,
            f"{d.get('experience', '?')} yrs",
        ])

    col_widths = [1*cm, 4.5*cm, 3.5*cm, 2*cm, 3*cm, 2.5*cm]
    comp_table = Table(tbl_data, colWidths=col_widths, repeatRows=1)
    comp_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), C_PRIMARY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, C_LIGHT_BG]),
        ("GRID",          (0, 0), (-1, -1), 0.4, C_BORDER),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("ALIGN",         (1, 1), (2, -1), "LEFT"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING",       (0, 0), (-1, -1), 6),
    ]))
    story.append(comp_table)

    # ══════════════════════════════════════════════════════════════════════════
    # Top 3 Candidates
    # ══════════════════════════════════════════════════════════════════════════
    if top3:
        story.append(Spacer(1, 0.5*cm))
        story.append(_hr())
        story.append(Paragraph("Top 3 Candidates", styles["SectionHeading"]))

        medals = ["🥇 #1", "🥈 #2", "🥉 #3"]
        top3_rows = [[]]
        top3_styles_list = [
            ("GRID",    (0, 0), (-1, -1), 0.4, C_BORDER),
            ("VALIGN",  (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]
        for i, (_, d) in enumerate(top3):
            status = d.get("candidate_status", "—")
            sc     = _status_color(status)
            cell_content = [
                Paragraph(f"<b>{medals[i]}</b>", styles["SubHeading"]),
                Paragraph(f"<b>{d.get('candidate_name','—')}</b>", styles["Body"]),
                Paragraph(f"Department: {d.get('department_fit','—')}", styles["Body"]),
                Paragraph(f"Match: <b>{d.get('match_percentage','?')}%</b>", styles["Body"]),
                Paragraph(
                    f'Status: <font color="{sc.hexval()}"><b>{status}</b></font>',
                    styles["Body"]
                ),
                Paragraph(f"Experience: {d.get('experience','?')} yrs", styles["Body"]),
            ]
            top3_rows[0].append(cell_content)
            top3_styles_list.append(
                ("BACKGROUND", (i, 0), (i, 0), C_LIGHT_BG)
            )

        top3_table = Table(top3_rows, colWidths=[5.3*cm] * len(top3))
        top3_table.setStyle(TableStyle(top3_styles_list))
        story.append(top3_table)

    # ══════════════════════════════════════════════════════════════════════════
    # Detailed Candidate Feedback (one section per candidate)
    # ══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("Detailed Candidate Feedback", styles["SectionHeading"]))
    story.append(_hr())

    for rank, (fname, d) in enumerate(successful, 1):
        status = d.get("candidate_status", "—")
        sc     = _status_color(status)

        # Candidate header
        story.append(Paragraph(
            f"#{rank} — {d.get('candidate_name', fname)}",
            styles["SubHeading"]
        ))
        story.append(Paragraph(
            f'Status: <font color="{sc.hexval()}"><b>{status}</b></font>  |  '
            f'Match: <b>{d.get("match_percentage","?")}%</b>  |  '
            f'Department: {d.get("department_fit","—")}  |  '
            f'Experience: {d.get("experience","?")} yrs',
            styles["Body"],
        ))

        # Matched / Missing skills
        matched = d.get("matched_skills", [])
        missing = d.get("missing_skills", [])
        story.append(Paragraph(
            f"<b>Matched Skills:</b> {', '.join(matched) if matched else '—'}",
            styles["Body"]
        ))
        story.append(Paragraph(
            f"<b>Missing Skills:</b> {', '.join(missing) if missing else '—'}",
            styles["Body"]
        ))

        # Strengths
        strengths = d.get("strengths", [])
        if strengths:
            story.append(Paragraph("<b>Strengths:</b>", styles["Body"]))
            for s in strengths:
                story.append(_bullet(s, styles["BulletItem"]))

        # Weaknesses
        weaknesses = d.get("weaknesses", [])
        if weaknesses:
            story.append(Paragraph("<b>Weaknesses:</b>", styles["Body"]))
            for w in weaknesses:
                story.append(_bullet(w, styles["BulletItem"]))

        # Evaluation reason
        reason = d.get("reason", "")
        if reason:
            story.append(Paragraph(f"<b>Evaluation:</b> {reason}", styles["Body"]))

        # Recruiter recommendation
        rec = d.get("recommendation", "")
        if rec:
            story.append(Paragraph(f"<b>Recommendation:</b> {rec}", styles["Body"]))

        story.append(Spacer(1, 0.2*cm))
        story.append(_hr())

    # ── Build ──────────────────────────────────────────────────────────────────
    doc.build(story)
    return buf.getvalue()
