"""
Generates a structured PDF report per assessed site/case using reportlab.
Always includes the mandatory disclaimer -- this is decision support, not
an engineering certification.
"""
import os
import sys
import uuid
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

DISCLAIMER = (
    "AI-generated assessment is decision support only. It does not replace "
    "qualified engineering inspection, emergency command, or official safety "
    "certification. All final decisions must be made by qualified personnel."
)


def generate_pdf_report(case_data: dict) -> str:
    """
    case_data: {
        "case_name": str,
        "disaster_type": str,
        "sites": [ { site_id, priority_score, priority_level, severity, ... } ],
        "team_assignments": [...],
    }
    Returns the path to the generated PDF.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    filename = f"report_{case_data.get('case_name', 'case')}_{uuid.uuid4().hex[:8]}.pdf"
    out_path = os.path.join(config.REPORTS_DIR, filename)

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(out_path, pagesize=A4)
    story = []

    story.append(Paragraph(f"Disaster-Resilient Infrastructure Assessment Report", styles["Title"]))
    story.append(Paragraph(f"Case: {case_data.get('case_name', 'N/A')} | Disaster type: {case_data.get('disaster_type', 'N/A')}", styles["Normal"]))
    story.append(Paragraph(f"Generated: {datetime.utcnow().isoformat()}Z", styles["Normal"]))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("Executive Summary", styles["Heading2"]))
    n_sites = len(case_data.get("sites", []))
    critical = sum(1 for s in case_data.get("sites", []) if s.get("priority_level") == "CRITICAL")
    story.append(Paragraph(f"{n_sites} sites assessed. {critical} flagged CRITICAL.", styles["Normal"]))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("Priority Ranking", styles["Heading2"]))
    table_data = [["Site ID", "Priority", "Level", "Severity", "Recommended Action"]]
    for s in sorted(case_data.get("sites", []), key=lambda x: -x.get("priority_score", 0)):
        table_data.append([
            s.get("site_id", ""),
            str(s.get("priority_score", "")),
            s.get("priority_level", ""),
            str(s.get("severity_score", "")),
            s.get("immediate_action", "")[:40],
        ])
    table = Table(table_data, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2a44")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.5 * cm))

    if case_data.get("team_assignments"):
        story.append(Paragraph("Team Allocation", styles["Heading2"]))
        assign_data = [["Site ID", "Team ID", "Match Score"]]
        for a in case_data["team_assignments"]:
            assign_data.append([a.get("site_id", ""), str(a.get("team_id", "UNASSIGNED")), str(a.get("match_score", ""))])
        assign_table = Table(assign_data, hAlign="LEFT")
        assign_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2a44")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]))
        story.append(assign_table)
        story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("Disclaimer", styles["Heading2"]))
    story.append(Paragraph(DISCLAIMER, styles["Normal"]))

    doc.build(story)
    return out_path
