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


_LEVEL_COLOR_HEX = {
    "CRITICAL": "#DC2626",
    "HIGH": "#F97316",
    "MEDIUM": "#F59E0B",
    "LOW": "#16A34A",
}


def _risk_bar_chart(sites, value_fn, title, max_value=None, value_suffix=""):
    """Horizontal bar chart, one bar per site, colored by that site's
    priority_level -- same red/orange/amber/green convention as the web
    report and the AI Assistant. Returns a reportlab Drawing, or None if
    there's nothing to plot. This was previously entirely missing from the
    PDF (only the web report had Chart.js bars) -- the PDF was tables only."""
    from reportlab.graphics.shapes import Drawing, String
    from reportlab.graphics.charts.barcharts import HorizontalBarChart
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.units import cm

    ranked = sorted(sites, key=lambda s: -(value_fn(s) or 0))[:10]  # cap for readability
    if not ranked:
        return None

    labels = [str(s.get("site_id", "?"))[:22] for s in ranked]
    values = [value_fn(s) or 0 for s in ranked]
    bar_colors = [rl_colors.HexColor(_LEVEL_COLOR_HEX.get(s.get("priority_level"), "#6B7280")) for s in ranked]

    row_h = 16
    height = max(60, row_h * len(ranked) + 30)
    width = 420
    drawing = Drawing(width, height + 20)
    drawing.add(String(0, height + 4, title, fontSize=10, fontName="Helvetica-Bold", fillColor=rl_colors.HexColor("#111827")))

    chart = HorizontalBarChart()
    chart.x = 110
    chart.y = 10
    chart.width = width - 130
    chart.height = height - 20
    chart.data = [values]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontSize = 7.5
    chart.valueAxis.valueMin = 0
    if max_value:
        chart.valueAxis.valueMax = max_value
    chart.valueAxis.labels.fontSize = 7
    chart.bars[0].fillColor = rl_colors.HexColor("#F97316")
    chart.barLabels.nudge = 6
    chart.barLabelFormat = f"%s{value_suffix}"
    chart.barLabels.fontSize = 7.5
    # Per-bar coloring -- HorizontalBarChart supports styling individual
    # bars via bars[(seriesIdx, barIdx)].
    for i, c in enumerate(bar_colors):
        chart.bars[(0, i)].fillColor = c
    drawing.add(chart)
    return drawing


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
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.5 * cm))

    # --- Visual Summary: the four bar charts the web report shows,
    # now actually rendered into the PDF too (previously text/tables only).
    sites_list = case_data.get("sites", [])
    if sites_list:
        story.append(Paragraph("Visual Summary", styles["Heading2"]))
        severity_chart = _risk_bar_chart(
            sites_list, lambda s: s.get("severity_score") or s.get("damage_severity"),
            "Severity by Site (0-10)", max_value=10,
        )
        priority_chart = _risk_bar_chart(
            sites_list, lambda s: s.get("priority_score"),
            "Priority by Site (0-100)", max_value=100,
        )
        population_chart = _risk_bar_chart(
            sites_list, lambda s: (s.get("population_data") or {}).get("estimated_affected_population"),
            "Population Impact by Site",
        )
        team_chart = _risk_bar_chart(
            sites_list, lambda s: (s.get("team_size") or {}).get("total_personnel"),
            "Recommended Team Size by Site",
        )
        for chart in (severity_chart, priority_chart, population_chart, team_chart):
            if chart is not None:
                story.append(chart)
                story.append(Spacer(1, 0.35 * cm))
        story.append(Spacer(1, 0.3 * cm))

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
