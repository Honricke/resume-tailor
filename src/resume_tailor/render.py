"""Resume JSON -> PDF via reportlab (no LaTeX). Single column, selectable text, ATS-friendly."""
import copy
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, KeepTogether, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

FONT, BOLD, ITALIC = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"

_BASE = ParagraphStyle("base", fontName=FONT, fontSize=9.5, leading=12.5)
STYLES = {
    "name": ParagraphStyle("name", parent=_BASE, fontName=BOLD, fontSize=18, leading=22, alignment=TA_CENTER),
    "label": ParagraphStyle("label", parent=_BASE, fontSize=10.5, leading=13, alignment=TA_CENTER),
    "contact": ParagraphStyle("contact", parent=_BASE, fontSize=9, alignment=TA_CENTER),
    "h": ParagraphStyle("h", parent=_BASE, fontName=BOLD, fontSize=11.5, leading=14, spaceBefore=9, spaceAfter=1),
    "title": ParagraphStyle("title", parent=_BASE, fontName=BOLD, fontSize=10, spaceBefore=4),
    "sub": ParagraphStyle("sub", parent=_BASE, fontName=ITALIC, fontSize=9),
    "body": _BASE,
}


_BASE_SIZES = {k: (v.fontSize, v.leading, v.spaceBefore) for k, v in STYLES.items()}


def _scale(factor: float) -> None:
    for k, (size, lead, before) in _BASE_SIZES.items():
        STYLES[k].fontSize, STYLES[k].leading, STYLES[k].spaceBefore = size * factor, lead * factor, before * factor


def _e(value) -> str:
    return escape(str(value)) if value not in (None, "") else ""


def _p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, STYLES[style])


def _join(parts, sep=" | ") -> str:
    return sep.join(p for p in parts if p)


def _dates(item: dict) -> str:
    start, end = _e(item.get("startDate")), _e(item.get("endDate"))
    return f"{start} - {end}" if start and end else start or end


def _bullets(items) -> list:
    items = [_e(i) for i in items or [] if i]
    if not items:
        return []
    return [ListFlowable(
        [ListItem(_p(i), leftIndent=12, bulletText="\u2022") for i in items],
        bulletType="bullet", start="•", leftIndent=12, bulletFontSize=8,
    )]


def _heading(title: str) -> list:
    return [_p(_e(title), "h"), HRFlowable(width="100%", thickness=0.6, color="black", spaceAfter=3)]


def _entry(title: str, sub: str, bullets) -> list:
    head = [_p(title, "title")] if title else []
    if sub:
        head.append(_p(sub, "sub"))
    body = _bullets(bullets)
    # keep heading with first lines of its bullets
    return [KeepTogether(head + body[:1])] if body else head


def _location(loc) -> str:
    if isinstance(loc, dict):
        return _e(_join([loc.get("city"), loc.get("region"), loc.get("countryCode")], ", "))
    return _e(loc)


def build_story(r: dict) -> list:
    b = r.get("basics", {})
    s = [_p(_e(b.get("name")), "name")]
    if b.get("label"):
        s.append(_p(_e(b["label"]), "label"))
    contact = [_e(b.get("email")), _e(b.get("phone")), _location(b.get("location")), _e(b.get("url"))]
    for pf in b.get("profiles") or []:
        contact.append(_e(pf.get("url") or _join([pf.get("network"), pf.get("username")], ": ")))
    s.append(_p(_join(contact), "contact"))

    if b.get("summary"):
        s += _heading("Summary") + [_p(_e(b["summary"]))]

    if r.get("skills"):
        s += _heading("Skills")
        for sk in r["skills"]:
            kw = ", ".join(_e(k) for k in sk.get("keywords") or [])
            s.append(_p(f"<b>{_e(sk.get('name'))}:</b> {kw}" if kw else f"<b>{_e(sk.get('name'))}</b>"))

    if r.get("work"):
        s += _heading("Work Experience")
        for j in r["work"]:
            title = _join([f"<b>{_e(j.get('position'))}</b>", _e(j.get("name"))], ", ")
            sub = _join([_dates(j), _location(j.get("location"))])
            s += _entry(title, sub, j.get("highlights"))

    if r.get("projects"):
        s += _heading("Projects")
        for p in r["projects"]:
            kw = ", ".join(_e(k) for k in p.get("keywords") or [])
            sub = _join([_e(p.get("url")), f"Stack: {kw}" if kw else ""])
            s += _entry(f"<b>{_e(p.get('name'))}</b>", sub, ([p["description"]] if p.get("description") else []) + list(p.get("highlights") or []))

    if r.get("education"):
        s += _heading("Education")
        for e in r["education"]:
            title = _join([f"<b>{_e(e.get('institution'))}</b>", _e(_join([e.get("studyType"), e.get("area")], " in "))], ", ")
            sub = _join([_dates(e), _location(e.get("location")), f"GPA: {_e(e['gpa'])}" if e.get("gpa") else ""])
            courses = [f"Courses: {', '.join(e['courses'])}"] if e.get("courses") else []
            s += _entry(title, sub, courses)

    if r.get("certificates"):
        s += _heading("Certifications")
        for c in r["certificates"]:
            s.append(_p(_join([f"<b>{_e(c.get('name'))}</b>", _e(c.get("issuer")), _e(c.get("date"))], " - ")))

    if r.get("languages"):
        s += _heading("Languages")
        for lg in r["languages"]:
            s.append(_p(_join([_e(lg.get("language")), _e(lg.get("fluency"))], " - ") if isinstance(lg, dict) else _e(lg)))

    if r.get("interests"):
        s += _heading("Interests")
        items = []
        for i in r["interests"]:
            if isinstance(i, dict):
                kw = ", ".join(_e(k) for k in i.get("keywords") or [])
                items.append(_join([_e(i.get("name")), kw], ": "))
            else:
                items.append(_e(i))
        s.append(_p(", ".join(x for x in items if x)))
    return s


def _build(resume: dict, target) -> int:
    """Builds the PDF into target (path or file object) and returns the page count."""
    name = str(resume.get("basics", {}).get("name", "Resume"))
    doc = SimpleDocTemplate(
        target, pagesize=A4, title=f"{name} - Resume", author=name,
        leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
    )
    doc.build(build_story(resume))
    return doc.page


def page_count(resume: dict) -> int:
    _scale(1.0)
    return _build(resume, BytesIO())


def _trim_one_bullet(resume: dict) -> bool:
    """Drops the last bullet of the entry with the most bullets (later entries first). False if none left."""
    best = None
    for section in ("work", "projects"):
        for item in resume.get(section) or []:
            n = len(item.get("highlights") or [])
            if n and (best is None or n >= len(best["highlights"])):
                best = item
    if best is None:
        return False
    best["highlights"].pop()
    return True


def fit_one_page(resume: dict) -> dict:
    """Returns a resume that renders on ONE page: shrinks type first, then drops the least important bullets."""
    resume = copy.deepcopy(resume)
    for factor in (1.0, 0.95, 0.9, 0.86):
        _scale(factor)
        if _build(resume, BytesIO()) <= 1:
            return resume
    while _trim_one_bullet(resume):
        if _build(resume, BytesIO()) <= 1:
            return resume
    resume["projects"] = []
    return resume


def render(resume: dict, out_dir: Path) -> Path:
    """Writes out_dir/resume.pdf (always one page) with reportlab and returns its path."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf = out_dir / "resume.pdf"
    fitted = fit_one_page(resume)
    _build(fitted, str(pdf))
    _scale(1.0)
    return pdf
