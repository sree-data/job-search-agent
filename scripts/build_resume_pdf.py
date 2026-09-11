import re
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, HRFlowable

SRC = "profile/resume-improved.md"
OUT = "profile/resume.pdf"

# ---- parse resume-improved.md: everything after the '---' separator ----
raw = open(SRC, encoding="utf-8").read()
body = raw.split("\n---\n", 1)[1]

def clean(t):
    t = t.replace("**", "").replace("`", "")
    return t.strip()

lines = [l.rstrip() for l in body.split("\n")]

name, contact = "", ""
sections = []          # (heading, [blocks])  block = ("p"|"b"|"role", text)
cur = None
blank = True
i = 0
while i < len(lines):
    l = lines[i]
    if not l.strip():
        blank = True
        i += 1; continue
    if l.startswith("## "):
        cur = (clean(l[3:]), [])
        sections.append(cur)
    elif l.startswith("### "):
        role = clean(l[4:])
        meta = clean(lines[i+1]) if i+1 < len(lines) else ""
        cur[1].append(("role", (role, meta)))
        i += 1
    elif l.startswith("- "):
        cur[1].append(("b", clean(l[2:])))
    else:
        if not name:
            name = clean(l)
        elif not contact:
            contact = clean(l)
        elif cur is not None:
            if cur[1] and cur[1][-1][0] == "p" and not blank:
                cur[1][-1] = ("p", cur[1][-1][1] + " " + clean(l))
            else:
                cur[1].append(("p", clean(l)))
    blank = False
    i += 1

# ATS: "Core stack" -> "Technical Skills"
sections = [("Technical Skills" if h == "Core stack" else h, b) for h, b in sections]

# ---- styles: single column, standard font, real text, no graphics ----
BODY = 9.3
st_name = ParagraphStyle("n", fontName="Helvetica-Bold", fontSize=16, leading=18,
                         spaceAfter=2, alignment=1)
st_contact = ParagraphStyle("c", fontName="Helvetica", fontSize=9.3, leading=11,
                            spaceAfter=7, alignment=1)
st_head = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=10.3, leading=12,
                         spaceBefore=7, spaceAfter=1)
st_role = ParagraphStyle("r", fontName="Helvetica-Bold", fontSize=9.8, leading=11.5,
                         spaceBefore=4.5, spaceAfter=0)
st_meta = ParagraphStyle("m", fontName="Helvetica-Oblique", fontSize=8.8, leading=10.5,
                         spaceAfter=2)
st_p = ParagraphStyle("p", fontName="Helvetica", fontSize=BODY, leading=11.6,
                      alignment=TA_JUSTIFY, spaceAfter=2)
st_b = ParagraphStyle("b", fontName="Helvetica", fontSize=BODY, leading=11.6,
                      alignment=TA_JUSTIFY, leftIndent=11, bulletIndent=1,
                      bulletFontName="Helvetica", bulletFontSize=BODY, spaceAfter=1.5)

story = [Paragraph(name, st_name), Paragraph(contact, st_contact)]
for head, blocks in sections:
    story.append(Paragraph(head.upper(), st_head))
    story.append(HRFlowable(width="100%", thickness=0.6, color="#000000",
                            spaceBefore=1, spaceAfter=3.5))
    bullets = []
    def flush():
        global bullets
        for b in bullets:
            story.append(Paragraph(b, st_b, bulletText="-"))
        bullets = []
    for kind, val in blocks:
        if kind == "role":
            flush()
            role, meta = val
            story.append(Paragraph(role, st_role))
            story.append(Paragraph(meta, st_meta))
        elif kind == "b":
            bullets.append(val)
        else:
            flush()
            story.append(Paragraph(val, st_p))
    flush()

doc = SimpleDocTemplate(OUT, pagesize=LETTER,
                        leftMargin=0.55*inch, rightMargin=0.55*inch,
                        topMargin=0.45*inch, bottomMargin=0.4*inch,
                        title="Alex Rivera - Resume", author="Alex Rivera",
                        subject="Data Engineer", creator="")
doc.build(story)
print("built", OUT)
