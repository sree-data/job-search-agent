#!/usr/bin/env python3
"""Build the three daily-summary deliverables from the pipeline.

  1. an HTML email body   (inline styles only, Gmail-on-iOS safe, no external assets)
  2. job-search-<date>.pdf         (reportlab platypus, designed for reading)
  3. job-search-tracker-<date>.xlsx (openpyxl, rebuilt from the CSVs each run)

Usage:
    python3 scripts/build_daily_report.py [--outdir pipeline/report] [--all-drafts]

Writes the three files plus attachments.json, which holds the base64 payloads in the
shape mcp__claude_ai_Gmail__send_message expects.
"""
from __future__ import annotations

import argparse
import base64
import csv
import html
import json
import os
import re
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICLOUD = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/JobSearch"
RETAIN_DAYS = 30
ACCENT = "#0F766E"      # single accent colour, used by both HTML and PDF
INK = "#1A1A1A"
MUTED = "#5C6B73"
RULE = "#D8DEE1"
CALLOUT_BG = "#F1F7F6"
ZEBRA = "#F4F6F7"

# --------------------------------------------------------------------------- input


def read_csv(name: str) -> list[dict]:
    p = ROOT / "pipeline" / f"{name}.csv"
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_summary() -> str:
    p = ROOT / "pipeline" / "daily-summary.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def section(md: str, heading_rx: str) -> str:
    """Return the body of the first '## heading' matching heading_rx."""
    m = re.search(rf"^##\s*{heading_rx}.*?$(.*?)(?=^##\s|\Z)", md, re.S | re.M | re.I)
    return m.group(1).strip() if m else ""


def inline_field(md: str, label: str) -> str:
    """Return the text of a '**Label:** ...' paragraph."""
    m = re.search(rf"^\*\*{label}:?\*\*:?\s*(.*?)(?=\n\s*\n|\Z)", md, re.S | re.M | re.I)
    return " ".join(m.group(1).split()) if m else ""


def strip_md(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]*)\*\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.strip()


def bullets(block: str) -> list[str]:
    out, cur = [], ""
    for line in block.splitlines():
        s = line.strip()
        if re.match(r"^(\d+\.|[-*])\s+", s):
            if cur:
                out.append(strip_md(cur))
            cur = re.sub(r"^(\d+\.|[-*])\s+", "", s)
        elif s and cur:
            cur += " " + s
        elif not s and cur:
            out.append(strip_md(cur))
            cur = ""
    if cur:
        out.append(strip_md(cur))
    return [b for b in out if b]


# --------------------------------------------------------------------------- drafts

DRAFT_RX = {
    "note": r"^##\s*A\..*?$(.*?)(?=^##\s|\Z)",
    "message": r"^##\s*B\..*?$(.*?)(?=^##\s|\Z)",
    "email": r"^##\s*C\..*?$(.*?)(?=^##\s|\Z)",
}


def parse_draft(path: Path) -> dict | None:
    if not path.exists():
        return None
    md = path.read_text(encoding="utf-8")
    head = re.search(r"^#\s*Outreach\s*[—-]\s*(.+)$", md, re.M)
    who = head.group(1).strip() if head else path.stem
    parts = [p.strip() for p in who.split(",")]
    name = parts[0]
    company = parts[-1] if len(parts) > 1 else ""
    title = ", ".join(parts[1:-1]) if len(parts) > 2 else (parts[1] if len(parts) == 2 else "")

    d = {"file": str(path.relative_to(ROOT)), "name": name, "title": title, "company": company}
    for key, rx in DRAFT_RX.items():
        m = re.search(rx, md, re.S | re.M)
        body = m.group(1).strip() if m else ""
        body = re.sub(r"^\s*\(?\d+\s*(characters|words).*$", "", body, flags=re.M).strip()
        if key == "email" and re.search(r"not written|no published", body, re.I):
            body = ""
        d[key] = body
    send = re.search(r"\*\*Send timing\.\*\*\s*(.+?)(?=\n\s*\n|\Z)", md, re.S)
    if not send:
        send = re.search(r"^Send\s+(.+?)$", md, re.M)
    d["send"] = " ".join(strip_md(send.group(1)).split()) if send else ""
    check = re.search(r"\*\*Before you send\.\*\*\s*(.+?)(?=\n\s*\n|\Z)", md, re.S)
    d["check"] = " ".join(strip_md(check.group(1)).split()) if check else ""
    return d


def todays_drafts(outreach: list[dict], all_drafts: bool) -> list[dict]:
    today = date.today()
    files, seen = [], set()
    for r in outreach:
        f = (r.get("draft_file") or "").strip()
        if not f or r.get("status") != "draft" or f in seen:
            continue
        p = ROOT / f
        if not p.exists():
            continue
        fresh = datetime.fromtimestamp(p.stat().st_mtime).date() == today
        if all_drafts or fresh:
            seen.add(f)
            files.append(p)
    if not files and not all_drafts:   # nothing new today: fall back, and say so
        return todays_drafts(outreach, True)
    return [d for d in (parse_draft(p) for p in files) if d]


# --------------------------------------------------------------------------- jobs

def todays_jobs(jobs: list[dict], limit: int = 8) -> list[dict]:
    today = str(date.today())
    new = [j for j in jobs if j.get("date_found") == today]
    rows = new or jobs
    rows = sorted(rows, key=lambda j: float(j.get("score") or 0), reverse=True)
    return rows[:limit]


# --------------------------------------------------------------------------- HTML

def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def html_body(ctx: dict) -> str:
    A, P = ACCENT, []
    add = P.append
    td = f'font-family:-apple-system,"Helvetica Neue",Arial,sans-serif;color:{INK};'

    add(f'<div style="background:#EEF2F3;margin:0;padding:16px 0;">')
    add(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="background:#EEF2F3;"><tr><td align="center">')
    add('<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" '
        'style="width:100%;max-width:600px;background:#FFFFFF;border-radius:10px;overflow:hidden;">')

    # header
    add(f'<tr><td style="background:{A};padding:20px 24px;">'
        f'<div style="{td}color:#FFFFFF;font-size:20px;font-weight:700;line-height:1.3;">'
        f'Job search daily</div>'
        f'<div style="{td}color:#CDE7E3;font-size:13px;padding-top:4px;">{esc(ctx["date_long"])}</div>'
        f'</td></tr>')

    # callout: replies + needs input
    add(f'<tr><td style="padding:20px 24px 0 24px;">')
    add(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="background:{CALLOUT_BG};border-left:4px solid {A};border-radius:6px;">'
        f'<tr><td style="padding:14px 16px;">')
    add(f'<div style="{td}font-size:12px;font-weight:700;letter-spacing:.06em;'
        f'text-transform:uppercase;color:{A};">Replies</div>')
    add(f'<div style="{td}font-size:15px;line-height:1.5;padding-top:4px;">'
        f'{esc(ctx["replies"]) or "None."}</div>')
    if ctx["followups"]:
        add(f'<div style="{td}font-size:14px;line-height:1.5;padding-top:10px;color:{MUTED};">'
            f'<b style="color:{INK};">Follow-ups.</b> {esc(ctx["followups"])}</div>')
    if ctx["needs"]:
        add(f'<div style="{td}font-size:12px;font-weight:700;letter-spacing:.06em;'
            f'text-transform:uppercase;color:{A};padding-top:14px;">Needs you</div>')
        add(f'<ul style="{td}font-size:14px;line-height:1.55;margin:6px 0 0 0;padding-left:20px;">')
        for b in ctx["needs"]:
            add(f'<li style="padding-bottom:5px;">{esc(b)}</li>')
        add('</ul>')
    add('</td></tr></table></td></tr>')

    # roles
    if ctx["jobs"]:
        add(f'<tr><td style="padding:22px 24px 0 24px;">'
            f'<div style="{td}font-size:16px;font-weight:700;">New roles</div>'
            f'<div style="height:2px;background:{A};width:36px;margin-top:6px;"></div></td></tr>')
        add('<tr><td style="padding:12px 24px 0 24px;">')
        add('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
            'style="width:100%;border-collapse:collapse;">')
        add(f'<tr>'
            f'<th align="left" style="{td}font-size:11px;letter-spacing:.05em;text-transform:uppercase;'
            f'color:{MUTED};padding:0 6px 8px 0;border-bottom:2px solid {RULE};">Company</th>'
            f'<th align="left" style="{td}font-size:11px;letter-spacing:.05em;text-transform:uppercase;'
            f'color:{MUTED};padding:0 6px 8px 6px;border-bottom:2px solid {RULE};">Role</th>'
            f'<th align="right" style="{td}font-size:11px;letter-spacing:.05em;text-transform:uppercase;'
            f'color:{MUTED};padding:0 0 8px 6px;border-bottom:2px solid {RULE};">Score</th></tr>')
        for i, j in enumerate(ctx["jobs"]):
            bg = ZEBRA if i % 2 else "#FFFFFF"
            title = esc(j.get("title", ""))
            if j.get("url"):
                title = f'<a href="{esc(j["url"])}" style="color:{A};text-decoration:none;">{title}</a>'
            add(f'<tr style="background:{bg};">'
                f'<td style="{td}font-size:14px;padding:9px 6px 9px 6px;border-bottom:1px solid {RULE};">'
                f'<b>{esc(j.get("company",""))}</b><br>'
                f'<span style="color:{MUTED};font-size:12px;">{esc(j.get("location","") or "Remote")}</span></td>'
                f'<td style="{td}font-size:14px;padding:9px 6px;border-bottom:1px solid {RULE};">{title}</td>'
                f'<td align="right" style="{td}font-size:14px;font-weight:700;padding:9px 6px;'
                f'border-bottom:1px solid {RULE};">{esc(j.get("score",""))}</td></tr>')
        add('</table></td></tr>')

    # drafts
    if ctx["drafts"]:
        add(f'<tr><td style="padding:24px 24px 0 24px;">'
            f'<div style="{td}font-size:16px;font-weight:700;">Drafts to send</div>'
            f'<div style="height:2px;background:{A};width:36px;margin-top:6px;"></div>'
            f'<div style="{td}font-size:13px;color:{MUTED};padding-top:8px;">'
            f'Long-press a block to select and copy.</div></td></tr>')
        mono = ('font-family:"SFMono-Regular",Menlo,Consolas,"Liberation Mono",monospace;'
                'font-size:13px;line-height:1.55;white-space:pre-wrap;word-wrap:break-word;'
                'margin:0;padding:12px 14px;background:#F7F9F9;border:1px solid ' + RULE + ';'
                'border-radius:6px;color:' + INK + ';')
        for d in ctx["drafts"]:
            add('<tr><td style="padding:14px 24px 0 24px;">')
            add(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
                f'style="border:1px solid {RULE};border-radius:8px;"><tr><td style="padding:14px 16px;">')
            add(f'<div style="{td}font-size:15px;font-weight:700;">{esc(d["name"])}</div>')
            sub = ", ".join(x for x in [d.get("title"), d.get("company")] if x)
            add(f'<div style="{td}font-size:13px;color:{MUTED};padding-top:2px;">{esc(sub)}</div>')
            if d.get("send"):
                add(f'<div style="{td}font-size:13px;padding-top:8px;">'
                    f'<b style="color:{A};">Send:</b> {esc(d["send"])}</div>')
            if d.get("check"):
                add(f'<div style="{td}font-size:12px;color:{MUTED};padding-top:4px;">'
                    f'{esc(d["check"])}</div>')
            for label, key in (("Connection note", "note"), ("Message", "message"), ("Email", "email")):
                if not d.get(key):
                    continue
                add(f'<div style="{td}font-size:11px;font-weight:700;letter-spacing:.05em;'
                    f'text-transform:uppercase;color:{MUTED};padding:12px 0 6px 0;">{label}</div>')
                add(f'<pre style="{mono}">{esc(d[key])}</pre>')
            add('</td></tr></table></td></tr>')

    # files in iCloud
    if ctx.get("files"):
        add(f'<tr><td style="padding:24px 24px 0 24px;">'
            f'<div style="{td}font-size:16px;font-weight:700;">Files</div>'
            f'<div style="height:2px;background:{A};width:36px;margin-top:6px;"></div></td></tr>')
        add('<tr><td style="padding:12px 24px 0 24px;">')
        add(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="background:{CALLOUT_BG};border-radius:6px;"><tr><td style="padding:14px 16px;">')
        for f in ctx["files"]:
            add(f'<div style="{td}font-size:14px;line-height:1.5;padding-bottom:8px;">'
                f'<a href="{esc(f["url"])}" style="color:{A};font-weight:700;text-decoration:none;">'
                f'{esc(f["name"])}</a> '
                f'<span style="color:{MUTED};font-size:12px;">{f["kb"]} KB</span><br>'
                f'<span style="color:{MUTED};font-size:12px;">{esc(f["path"])}</span></div>')
        add(f'<div style="{td}font-size:12px;color:{MUTED};padding-top:2px;">'
            f'On iPhone: Files app, iCloud Drive, {esc(ctx["icloud_folder"])}. '
            f'Kept for {RETAIN_DAYS} days.</div>')
        add('</td></tr></table></td></tr>')

    # counts + footer
    if ctx["counts"]:
        add(f'<tr><td style="padding:22px 24px 0 24px;">'
            f'<div style="{td}font-size:13px;color:{MUTED};border-top:1px solid {RULE};padding-top:12px;">'
            f'{esc(ctx["counts"])}</div></td></tr>')
    add(f'<tr><td style="padding:14px 24px 24px 24px;">'
        f'<div style="{td}font-size:12px;color:{MUTED};">'
        f'PDF and tracker are in iCloud Drive, linked above. Nothing here has been sent to anyone but you.</div></td></tr>')

    add('</table></td></tr></table></div>')
    return "\n".join(P)


# --------------------------------------------------------------------------- PDF

def build_pdf(ctx: dict, out: Path) -> Path:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (BaseDocTemplate, Frame, HRFlowable, KeepTogether,
                                    PageTemplate, Paragraph, Spacer, Table, TableStyle)

    acc = colors.HexColor(ACCENT)
    ink = colors.HexColor(INK)
    muted = colors.HexColor(MUTED)
    rule = colors.HexColor(RULE)

    S = {
        "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=20, leading=24,
                             textColor=ink, spaceAfter=2),
        "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=10.5, leading=13,
                              textColor=muted, spaceAfter=14),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13, leading=16,
                             textColor=ink, spaceBefore=16, spaceAfter=4),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=14.5,
                               textColor=ink, alignment=TA_LEFT),
        "small": ParagraphStyle("small", fontName="Helvetica", fontSize=9, leading=12.5,
                                textColor=muted),
        "kicker": ParagraphStyle("kicker", fontName="Helvetica-Bold", fontSize=8.5, leading=11,
                                 textColor=acc, spaceAfter=3),
        "cardname": ParagraphStyle("cardname", fontName="Helvetica-Bold", fontSize=12,
                                   leading=15, textColor=ink),
        "mono": ParagraphStyle("mono", fontName="Courier", fontSize=8.8, leading=12.4,
                               textColor=ink),
        "th": ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=8.5, leading=11,
                             textColor=colors.white),
        "td": ParagraphStyle("td", fontName="Helvetica", fontSize=9.5, leading=12.5,
                             textColor=ink),
    }

    def P(t, s="body"):
        return Paragraph(html.escape(t or "").replace("\n", "<br/>"), S[s])

    story = []
    story.append(Paragraph("Job search daily", S["h1"]))
    story.append(Paragraph(ctx["date_long"], S["sub"]))

    # callout
    cell = [Paragraph("REPLIES", S["kicker"]), P(ctx["replies"] or "None.")]
    if ctx["followups"]:
        cell += [Spacer(1, 6), P(f"Follow-ups. {ctx['followups']}", "small")]
    if ctx["needs"]:
        cell += [Spacer(1, 10), Paragraph("NEEDS YOU", S["kicker"])]
        for i, b in enumerate(ctx["needs"], 1):
            cell.append(P(f"{i}.  {b}"))
            cell.append(Spacer(1, 3))
    box = Table([[cell]], colWidths=[6.9 * inch])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(CALLOUT_BG)),
        ("LINEBEFORE", (0, 0), (0, -1), 3, acc),
        ("BOX", (0, 0), (-1, -1), 0.5, rule),
        ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(box)

    # roles
    if ctx["jobs"]:
        story.append(Paragraph("New roles", S["h2"]))
        story.append(HRFlowable(width="100%", thickness=1.2, color=acc, spaceAfter=8))
        data = [[Paragraph(h, S["th"]) for h in ("Company", "Role", "Location", "Spon.", "Score")]]
        for j in ctx["jobs"]:
            data.append([
                Paragraph(html.escape(j.get("company", "")), S["td"]),
                Paragraph(html.escape(j.get("title", "")), S["td"]),
                Paragraph(html.escape(j.get("location", "") or "Remote"), S["td"]),
                Paragraph(html.escape(j.get("sponsorship_signal", "")), S["td"]),
                Paragraph(html.escape(str(j.get("score", ""))), S["td"]),
            ])
        t = Table(data, colWidths=[1.5 * inch, 2.5 * inch, 1.45 * inch, .65 * inch, .5 * inch],
                  repeatRows=1)
        st = [("BACKGROUND", (0, 0), (-1, 0), acc),
              ("VALIGN", (0, 0), (-1, -1), "TOP"),
              ("LINEBELOW", (0, 0), (-1, -1), 0.4, rule),
              ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
              ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]
        for i in range(1, len(data)):
            if i % 2 == 0:
                st.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor(ZEBRA)))
        t.setStyle(TableStyle(st))
        story.append(t)

    # draft cards
    if ctx["drafts"]:
        story.append(Paragraph("Drafts to send", S["h2"]))
        story.append(HRFlowable(width="100%", thickness=1.2, color=acc, spaceAfter=8))
        for d in ctx["drafts"]:
            inner = [Paragraph(html.escape(d["name"]), S["cardname"])]
            sub = ", ".join(x for x in [d.get("title"), d.get("company")] if x)
            if sub:
                inner.append(P(sub, "small"))
            if d.get("send"):
                inner += [Spacer(1, 5), P(f"Send: {d['send']}", "small")]
            for label, key in (("CONNECTION NOTE", "note"), ("MESSAGE", "message"), ("EMAIL", "email")):
                if not d.get(key):
                    continue
                inner += [Spacer(1, 9), Paragraph(label, S["kicker"]), P(d[key], "mono")]
            if d.get("check"):
                inner += [Spacer(1, 8), P(d["check"], "small")]
            card = Table([[inner]], colWidths=[6.9 * inch])
            card.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.8, rule),
                ("LINEBEFORE", (0, 0), (0, -1), 2.5, acc),
                ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 11), ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
            ]))
            story.append(KeepTogether(card))
            story.append(Spacer(1, 10))

    if ctx["counts"]:
        story.append(HRFlowable(width="100%", thickness=0.6, color=rule, spaceBefore=10, spaceAfter=6))
        story.append(P(ctx["counts"], "small"))

    def decorate(canv, doc):
        canv.saveState()
        canv.setFont("Helvetica", 8)
        canv.setFillColor(muted)
        canv.drawString(0.8 * inch, LETTER[1] - 0.52 * inch, "Job search daily")
        canv.drawRightString(LETTER[0] - 0.8 * inch, LETTER[1] - 0.52 * inch, ctx["date_iso"])
        canv.setStrokeColor(rule)
        canv.setLineWidth(0.5)
        canv.line(0.8 * inch, LETTER[1] - 0.62 * inch, LETTER[0] - 0.8 * inch, LETTER[1] - 0.62 * inch)
        canv.drawCentredString(LETTER[0] / 2, 0.5 * inch, f"Page {canv._pageNumber}")
        canv.restoreState()

    doc = BaseDocTemplate(str(out), pagesize=LETTER,
                          leftMargin=0.8 * inch, rightMargin=0.8 * inch,
                          topMargin=0.85 * inch, bottomMargin=0.8 * inch,
                          pageCompression=1, invariant=1,
                          title=f"Job search daily {ctx['date_iso']}", author="Alex Rivera")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=decorate)])
    doc.build(story)
    return out


# --------------------------------------------------------------------------- XLSX

FILLS = {
    "green": "C6EFCE", "amber": "FFEB9C", "red": "FFC7CE",
    "blue": "DDEBF7", "purple": "E4DFEC", "grey": "EDEDED",
}
STATUS_COLOR = {
    "new": "blue", "pursuing": "green", "applied": "green", "paused": "grey",
    "draft": "amber", "approved": "blue", "sent": "green", "replied": "purple",
    "yes": "green", "unknown": "amber", "no": "red",
}


def build_xlsx(ctx: dict, out: Path) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    head_fill = PatternFill("solid", fgColor=ACCENT.lstrip("#"))
    head_font = Font(bold=True, color="FFFFFF", size=11)
    thin = Side(style="thin", color="D8DEE1")
    border = Border(bottom=thin)

    def sheet(name, rows, color_cols=()):
        ws = wb.create_sheet(name)
        if not rows:
            ws["A1"] = "(empty)"
            return ws
        cols = list(rows[0].keys())
        ws.append(cols)
        for c in range(1, len(cols) + 1):
            cell = ws.cell(row=1, column=c)
            cell.fill, cell.font = head_fill, head_font
            cell.alignment = Alignment(vertical="center")
        for r in rows:
            ws.append([r.get(c, "") for c in cols])
        for idx, cname in enumerate(cols, start=1):
            width = max([len(str(cname))] + [len(str(r.get(cname, ""))) for r in rows]) + 2
            ws.column_dimensions[get_column_letter(idx)].width = min(max(width, 9), 52)
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=len(cols)):
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
                cell.border = border
        for cname in color_cols:
            if cname not in cols:
                continue
            ci = cols.index(cname) + 1
            for r in range(2, ws.max_row + 1):
                key = str(ws.cell(row=r, column=ci).value or "").strip().lower()
                col = STATUS_COLOR.get(key)
                if col:
                    ws.cell(row=r, column=ci).fill = PatternFill("solid", fgColor=FILLS[col])
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{ws.max_row}"
        return ws

    # Summary first
    ws = wb.active
    ws.title = "Summary"
    out_rows = ctx["outreach"]
    sent = [r for r in out_rows if r.get("status") in ("sent", "replied")]
    replied = [r for r in out_rows if (r.get("reply") or "").strip() or r.get("status") == "replied"]
    rate = f"{len(replied) / len(sent):.0%}" if sent else "n/a (nothing sent yet)"
    stats = [
        ("Report date", ctx["date_iso"]),
        ("", ""),
        ("Roles in pipeline", len(ctx["all_jobs"])),
        ("Roles added today", len([j for j in ctx["all_jobs"] if j.get("date_found") == ctx["date_iso"]])),
        ("Contacts identified", len(ctx["contacts"])),
        ("Outreach pieces total", len(out_rows)),
        ("Drafts awaiting send", len([r for r in out_rows if r.get("status") == "draft"])),
        ("Messages sent", len(sent)),
        ("Replies received", len(replied)),
        ("Reply rate", rate),
    ]
    ws["A1"] = "Job search tracker"
    ws["A1"].font = Font(bold=True, size=16, color=ACCENT.lstrip("#"))
    ws["A2"] = ctx["date_long"]
    ws["A2"].font = Font(size=10, color="5C6B73")
    for i, (k, v) in enumerate(stats, start=4):
        ws.cell(row=i, column=1, value=k).font = Font(bold=bool(k))
        ws.cell(row=i, column=2, value=v)
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 30
    ws.freeze_panes = "A4"

    sheet("Jobs", ctx["all_jobs"], color_cols=("status", "sponsorship_signal"))
    sheet("Contacts", ctx["contacts"], color_cols=("type",))
    sheet("Outreach", out_rows, color_cols=("status",))
    wb.save(out)
    return out


# ----------------------------------------------------------------- icloud delivery

def publish(files: list[Path], dest: Path) -> list[dict]:
    """Copy the built files into iCloud Drive and describe them for the email."""
    import shutil
    dest.mkdir(parents=True, exist_ok=True)
    out = []
    for f in files:
        target = dest / f.name
        shutil.copy2(f, target)
        out.append({
            "name": f.name,
            "kb": max(1, round(target.stat().st_size / 1024)),
            # best-effort tap target on iOS; the Files path below is the reliable route
            "url": "shareddocuments://" + str(target).replace(" ", "%20"),
            "path": f"iCloud Drive / {dest.name} / {f.name}",
        })
    return out


def prune(dest: Path, days: int = RETAIN_DAYS) -> list[str]:
    """Keep a rolling window; delete older generated reports. Only touches our own names."""
    import time
    if not dest.exists():
        return []
    cutoff = time.time() - days * 86400
    removed = []
    for f in list(dest.glob("job-search-*.pdf")) + list(dest.glob("job-search-tracker-*.xlsx")):
        if f.is_file() and f.stat().st_mtime < cutoff:
            f.unlink()
            removed.append(f.name)
    return removed


# --------------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="pipeline/report")
    ap.add_argument("--all-drafts", action="store_true")
    ap.add_argument("--icloud", default=str(ICLOUD))
    args = ap.parse_args()

    outdir = ROOT / args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    md = read_summary()
    jobs, contacts, outreach = read_csv("jobs"), read_csv("contacts"), read_csv("outreach")
    today = date.today()

    needs_block = section(md, r"Needs your input")
    ctx = {
        "date_iso": today.isoformat(),
        "date_long": today.strftime("%A, %d %B %Y"),
        "replies": strip_md(inline_field(md, "Replies received")),
        "followups": strip_md(inline_field(md, "Follow-ups drafted")),
        "needs": bullets(needs_block)[:8],
        "counts": strip_md(section(md, r"Pipeline counts")).replace("\n", " "),
        "jobs": todays_jobs(jobs),
        "all_jobs": jobs,
        "contacts": contacts,
        "outreach": outreach,
        "drafts": todays_drafts(outreach, args.all_drafts),
    }

    # build the documents first, publish them, then render the email around them
    pdf = build_pdf(ctx, outdir / f"job-search-{ctx['date_iso']}.pdf")
    xlsx = build_xlsx(ctx, outdir / f"job-search-tracker-{ctx['date_iso']}.xlsx")

    dest = Path(args.icloud).expanduser()
    ctx["icloud_folder"] = dest.name
    published, removed = [], []
    try:
        published = publish([pdf, xlsx], dest)
        removed = prune(dest)
    except OSError as e:
        print(f"WARNING: could not publish to {dest}: {e}")
    ctx["files"] = published

    html_path = outdir / "daily-email.html"
    html_path.write_text(html_body(ctx), encoding="utf-8")

    meta = {
        "subject": f"Job search daily — {ctx['date_iso']}",
        "html_file": str(html_path.relative_to(ROOT)),
        "attachments": [],          # delivery is via iCloud Drive, not attachments
        "icloud_dir": str(dest),
        "published": published,
        "pruned": removed,
    }
    (outdir / "report-meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"html   {html_path.relative_to(ROOT)}  {html_path.stat().st_size:,} bytes")
    print(f"pdf    {pdf.name}  {pdf.stat().st_size:,} bytes")
    print(f"xlsx   {xlsx.name}  {xlsx.stat().st_size:,} bytes")
    print(f"icloud {dest}")
    for f in published:
        print(f"   published {f['name']}  {f['kb']} KB")
    print(f"   pruned {len(removed)} file(s) older than {RETAIN_DAYS} days"
          + (": " + ", ".join(removed) if removed else ""))
    print(f"drafts rendered: {len(ctx['drafts'])}   roles: {len(ctx['jobs'])}")


if __name__ == "__main__":
    main()
