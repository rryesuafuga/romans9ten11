"""Render one simple document model to Markdown, DOCX and PDF. Standard library only.

A document is a list of blocks (dicts with key "t"):

    title      {"text"}
    subtitle   {"text"}
    meta       {"runs"}
    epigraph   {"text", "ref"}
    h1         {"text"}
    h2         {"text"}
    para       {"runs"}
    glance     {"items": [(number, runs)]}     numbered "at a glance" list
    scripture  {"verses": [(chapter, verse, text)], "ref", "testament"}
    prayer     {"paras": [str]}
    rule       {}

A run is {"text", "b": bool, "i": bool, "url": str|None}.

PDF: write_pdf() is the default. It uses the PDF core fonts (Times, Helvetica)
and needs nothing but Python, so the output is the same in every environment.
docx_to_pdf() is an optional LibreOffice conversion; it needs the Writer
component, which the default Claude Code cloud image does not include.
"""
import datetime as _dt
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
import zlib
from xml.sax.saxutils import escape as _xesc

ACCENT = "0038B8"      # blue of the Israeli flag
ACCENT_SOFT = "EEF2FB"
INK = "1F2933"
MUTED = "5B6770"


def R(text, b=False, i=False, url=None):
    return {"text": text, "b": b, "i": i, "url": url}


# ----------------------------------------------------------------- Markdown

def _md_escape(s):
    return re.sub(r"([\\`*_\[\]<>])", r"\\\1", s)


def _md_runs(runs):
    out = []
    for r in runs:
        t = _md_escape(r["text"])
        lead = re.match(r"^\s*", t).group(0)
        trail = re.search(r"\s*$", t).group(0)
        core = t.strip()
        if core:
            if r.get("b") and r.get("i"):
                core = f"***{core}***"
            elif r.get("b"):
                core = f"**{core}**"
            elif r.get("i"):
                core = f"*{core}*"
            if r.get("url"):
                core = f"[{core}]({r['url']})"
        out.append(lead + core + trail if core else t)
    return "".join(out)


def to_markdown(blocks):
    lines = []
    for b in blocks:
        t = b["t"]
        if t == "title":
            lines += [f"# {b['text']}", ""]
        elif t == "subtitle":
            lines += [f"*{_md_escape(b['text'])}*", ""]
        elif t == "meta":
            lines += [_md_runs(b["runs"]), ""]
        elif t == "epigraph":
            lines += [f"> *{_md_escape(b['text'])}*", f"> <br>— {b['ref']} (KJV)", ""]
        elif t == "h1":
            lines += [f"## {b['text']}", ""]
        elif t == "h2":
            lines += [f"### {b['text']}", ""]
        elif t == "para":
            lines += [_md_runs(b["runs"]), ""]
        elif t == "glance":
            for n, runs in b["items"]:
                lines.append(f"{n}. {_md_runs(runs)}")
            lines.append("")
        elif t == "scripture":
            multi = len(b["verses"]) > 1
            body = " ".join(
                (f"<sup>{v}</sup> " if multi else "") + _md_escape(txt) for _, v, txt in b["verses"]
            )
            lines += [f"> *{body}*" if not multi else f"> {body}", ">",
                      f"> — **{b['ref']}** · KJV · {b['testament']}", ""]
        elif t == "prayer":
            first = True
            for p in b["paras"]:
                lines += [("**Prayer:** " if first else "") + _md_escape(p), ""]
                first = False
        elif t == "rule":
            lines += ["---", ""]
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------- DOCX

W_NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')


def _x(s):
    return _xesc(s, {'"': "&quot;"})


class _Docx:
    def __init__(self):
        self.links = []

    def link_id(self, url):
        if url not in self.links:
            self.links.append(url)
        return f"rIdL{self.links.index(url) + 1}"

    def run(self, text, b=False, i=False, color=None, size=None, sup=False, style=None, font=None):
        rpr = []
        if style:
            rpr.append(f'<w:rStyle w:val="{style}"/>')
        if font:
            rpr.append(f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}"/>')
        if b:
            rpr.append("<w:b/><w:bCs/>")
        if i:
            rpr.append("<w:i/><w:iCs/>")
        if color:
            rpr.append(f'<w:color w:val="{color}"/>')
        if size:
            rpr.append(f'<w:sz w:val="{int(size * 2)}"/><w:szCs w:val="{int(size * 2)}"/>')
        if sup:
            if not i:
                rpr.append('<w:i w:val="0"/><w:iCs w:val="0"/>')
            rpr.append('<w:vertAlign w:val="superscript"/>')
        rp = f"<w:rPr>{''.join(rpr)}</w:rPr>" if rpr else ""
        return f'<w:r>{rp}<w:t xml:space="preserve">{_x(text)}</w:t></w:r>'

    def runs(self, runs, **kw):
        out = []
        for r in runs:
            if r.get("url"):
                rid = self.link_id(r["url"])
                out.append(f'<w:hyperlink r:id="{rid}" w:history="1">'
                           + self.run(r["text"], b=r.get("b"), i=r.get("i"), style="Hyperlink", **kw)
                           + "</w:hyperlink>")
            else:
                out.append(self.run(r["text"], b=r.get("b"), i=r.get("i"), **kw))
        return "".join(out)

    @staticmethod
    def p(style, content, extra_ppr=""):
        return f'<w:p><w:pPr><w:pStyle w:val="{style}"/>{extra_ppr}</w:pPr>{content}</w:p>'


def _docx_styles():
    def pstyle(sid, name, ppr="", rpr="", based="Normal", nxt="Normal", q=False):
        return (f'<w:style w:type="paragraph" w:customStyle="1" w:styleId="{sid}"><w:name w:val="{name}"/>'
                f'<w:basedOn w:val="{based}"/><w:next w:val="{nxt}"/>{"<w:qFormat/>" if q else ""}'
                f'<w:pPr>{ppr}</w:pPr><w:rPr>{rpr}</w:rPr></w:style>')
    sans = '<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>'
    box = (f'<w:pBdr><w:left w:val="single" w:sz="24" w:space="10" w:color="{ACCENT}"/></w:pBdr>'
           f'<w:shd w:val="clear" w:color="auto" w:fill="{ACCENT_SOFT}"/><w:ind w:left="340" w:right="340"/>')
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles {W_NS}>
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman" w:eastAsia="Times New Roman"/>
<w:color w:val="{INK}"/><w:sz w:val="24"/><w:szCs w:val="24"/><w:lang w:val="en-GB"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="288" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>
{pstyle("Title", "Title", '<w:spacing w:after="60"/>', sans + f'<w:b/><w:color w:val="{ACCENT}"/><w:sz w:val="44"/>', q=True)}
{pstyle("Subtitle", "Subtitle", '<w:spacing w:after="120"/>', f'<w:i/><w:color w:val="{MUTED}"/><w:sz w:val="26"/>', q=True)}
{pstyle("Meta", "Meta", '<w:spacing w:after="200"/>', sans + f'<w:color w:val="{MUTED}"/><w:sz w:val="18"/>')}
{pstyle("Epigraph", "Epigraph", '<w:spacing w:before="120" w:after="240"/><w:ind w:left="567" w:right="567"/><w:jc w:val="center"/>', f'<w:i/><w:color w:val="{MUTED}"/>')}
{pstyle("Heading1", "heading 1", f'<w:keepNext/><w:spacing w:before="360" w:after="160"/><w:pBdr><w:bottom w:val="single" w:sz="8" w:space="4" w:color="{ACCENT}"/></w:pBdr><w:outlineLvl w:val="0"/>', sans + f'<w:b/><w:color w:val="{ACCENT}"/><w:sz w:val="30"/>', q=True)}
{pstyle("Heading2", "heading 2", '<w:keepNext/><w:keepLines/><w:spacing w:before="280" w:after="100"/><w:outlineLvl w:val="1"/>', sans + '<w:b/><w:sz w:val="25"/>', q=True)}
{pstyle("Glance", "Glance", '<w:spacing w:after="40"/><w:tabs><w:tab w:val="left" w:pos="425"/></w:tabs><w:ind w:left="425" w:hanging="425"/>', '<w:sz w:val="22"/>')}
{pstyle("NewsLine", "News line", '<w:keepNext/><w:spacing w:after="100"/>', sans + '<w:sz w:val="20"/>')}
{pstyle("Scripture", "Scripture", '<w:keepNext/><w:keepLines/><w:spacing w:before="60" w:after="0"/>' + box, '<w:i/>')}
{pstyle("ScriptureRef", "Scripture reference", '<w:keepNext/><w:spacing w:before="40" w:after="160"/>' + box, sans + f'<w:b/><w:color w:val="{ACCENT}"/><w:sz w:val="19"/>')}
{pstyle("Prayer", "Prayer", '<w:spacing w:after="160"/>')}
{pstyle("Closing", "Closing", '<w:spacing w:before="120" w:after="160"/>', '<w:i/>')}
<w:style w:type="character" w:styleId="Hyperlink"><w:name w:val="Hyperlink"/><w:rPr><w:color w:val="{ACCENT}"/><w:u w:val="single"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Footer"><w:name w:val="footer"/><w:basedOn w:val="Normal"/><w:pPr><w:jc w:val="center"/><w:spacing w:after="0"/></w:pPr><w:rPr>{sans}<w:color w:val="{MUTED}"/><w:sz w:val="16"/></w:rPr></w:style>
</w:styles>'''


def write_docx(blocks, path, title, footer_text, author="romans9ten11 daily routine"):
    d = _Docx()
    body = []
    for b in blocks:
        t = b["t"]
        if t == "title":
            body.append(d.p("Title", d.run(b["text"])))
        elif t == "subtitle":
            body.append(d.p("Subtitle", d.run(b["text"])))
        elif t == "meta":
            body.append(d.p("Meta", d.runs(b["runs"])))
        elif t == "epigraph":
            body.append(d.p("Epigraph", d.run(b["text"]) + '<w:r><w:br/></w:r>' + d.run(f"— {b['ref']} (KJV)")))
        elif t == "h1":
            body.append(d.p("Heading1", d.run(b["text"])))
        elif t == "h2":
            body.append(d.p("Heading2", d.run(b["text"])))
        elif t == "para":
            style = b.get("style", "Normal")
            body.append(d.p(style, d.runs(b["runs"])))
        elif t == "glance":
            for n, runs in b["items"]:
                body.append(d.p("Glance", d.run(f"{n}.", b=True, color=ACCENT) + '<w:r><w:tab/></w:r>' + d.runs(runs)))
        elif t == "scripture":
            multi = len(b["verses"]) > 1
            parts = []
            for _, v, txt in b["verses"]:
                if multi:
                    parts.append(d.run(str(v), sup=True, color=ACCENT, i=False))
                    parts.append(d.run(" " + txt + " "))
                else:
                    parts.append(d.run(txt))
            body.append(d.p("Scripture", "".join(parts)))
            body.append(d.p("ScriptureRef", d.run(f"— {b['ref']}  ·  KJV  ·  {b['testament']}")))
        elif t == "prayer":
            first = True
            for ptxt in b["paras"]:
                lead = d.run("Prayer: ", b=True, color=ACCENT) if first else ""
                body.append(d.p("Prayer", lead + d.run(ptxt)))
                first = False
        elif t == "rule":
            body.append(f'<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="6" w:space="1" w:color="C9D2E3"/></w:pBdr></w:pPr></w:p>')
    sect = ('<w:sectPr><w:footerReference w:type="default" r:id="rIdFooter"/>'
            '<w:pgSz w:w="11906" w:h="16838"/>'
            '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="567" w:footer="567" w:gutter="0"/>'
            '</w:sectPr>')
    document = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:document {W_NS}><w:body>'
                + "".join(body) + sect + "</w:body></w:document>")
    footer = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:ftr {W_NS}><w:p><w:pPr><w:pStyle w:val="Footer"/></w:pPr>'
              f'<w:r><w:t xml:space="preserve">{_x(footer_text)}  ·  Page </w:t></w:r>'
              '<w:fldSimple w:instr=" PAGE "><w:r><w:t>1</w:t></w:r></w:fldSimple>'
              '<w:r><w:t xml:space="preserve"> of </w:t></w:r>'
              '<w:fldSimple w:instr=" NUMPAGES "><w:r><w:t>1</w:t></w:r></w:fldSimple></w:p></w:ftr>')
    rels = ['<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>',
            '<Relationship Id="rIdSettings" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>',
            '<Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>']
    for i, url in enumerate(d.links):
        rels.append(f'<Relationship Id="rIdL{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="{_x(url)}" TargetMode="External"/>')
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    files = {
        "[Content_Types].xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>''',
        "_rels/.rels": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>''',
        "word/_rels/document.xml.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + "".join(rels) + "</Relationships>",
        "word/document.xml": document,
        "word/styles.xml": _docx_styles(),
        "word/settings.xml": f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:settings {W_NS}><w:updateFields w:val="false"/><w:defaultTabStop w:val="720"/><w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat></w:settings>',
        "word/footer1.xml": footer,
        "docProps/core.xml": f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:title>{_x(title)}</dc:title><dc:creator>{_x(author)}</dc:creator><dc:language>en-GB</dc:language>
<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
</cp:coreProperties>''',
        "docProps/app.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>romans9ten11 build_prayer.py</Application></Properties>',
    }
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for name in ["[Content_Types].xml", "_rels/.rels", "word/_rels/document.xml.rels", "word/document.xml",
                     "word/styles.xml", "word/settings.xml", "word/footer1.xml", "docProps/core.xml", "docProps/app.xml"]:
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, files[name])
    os.replace(tmp, path)


def docx_to_pdf(docx_path, pdf_path, timeout=180):
    """Convert with LibreOffice. Returns True on success, False if unavailable or it failed."""
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    if not exe:
        return False
    with tempfile.TemporaryDirectory() as td:
        profile = "file://" + os.path.join(td, "profile")
        cmd = [exe, f"-env:UserInstallation={profile}", "--headless", "--norestore",
               "--convert-to", "pdf", "--outdir", td, docx_path]
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)
        except (subprocess.TimeoutExpired, OSError):
            return False
        out = os.path.join(td, os.path.splitext(os.path.basename(docx_path))[0] + ".pdf")
        if not os.path.exists(out) or os.path.getsize(out) < 1000:
            return False
        with open(out, "rb") as fh:
            if not fh.read(5).startswith(b"%PDF"):
                return False
        shutil.move(out, pdf_path)
    return True


# ---------------------------------------------------------------------- PDF

def _hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


_PDF_FONTS = {"rm": "Times-Roman", "bd": "Times-Bold", "it": "Times-Italic", "bi": "Times-BoldItalic",
              "sans": "Helvetica", "sansb": "Helvetica-Bold", "sansi": "Helvetica-Oblique"}
_FONT_RES = {k: f"F{i + 1}" for i, k in enumerate(_PDF_FONTS)}


def _enc(s):
    s = s.replace("‑", "-").replace(" ", " ")
    return s.encode("cp1252", errors="replace")


def _width(s, font, size):
    from pdf_metrics import WIDTHS  # noqa: WPS433 (local import keeps module optional)
    w = WIDTHS[_PDF_FONTS[font]]
    total = 0
    for byte in _enc(s):
        total += w[byte - 32] if 32 <= byte <= 255 else 500
    return total * size / 1000.0


def _pdf_str(s):
    raw = _enc(s)
    return b"(" + raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)") + b")"


def write_pdf(blocks, path, title, footer_text):
    """Built-in PDF writer (core fonts, A4). Used when LibreOffice is not available."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    PW, PH, M = 595.28, 841.89, 56.7
    TW = PW - 2 * M
    pages = []          # list of (ops list, annots list)
    state = {"y": PH - M, "ops": None, "annots": None}

    def new_page():
        state["ops"], state["annots"] = [], []
        pages.append((state["ops"], state["annots"]))
        state["y"] = PH - M

    new_page()

    def ensure(h):
        if state["y"] - h < M + 20:
            new_page()

    def layout(runs, width, size, lead):
        """runs: list of (text, font, color, url, sup). Returns list of lines; a line is list of
        (x, text, font, size, color, url, rise)."""
        words = []
        for text, font, color, url, sup in runs:
            for tok in re.findall(r"\S+\s*|\s+", text):
                words.append((tok, font, color, url, sup))
        lines, line, x = [], [], 0.0
        for tok, font, color, url, sup in words:
            fs = size * (0.62 if sup else 1.0)
            w = _width(tok.rstrip(), font, fs)
            wsp = _width(tok, font, fs)
            if line and x + w > width:
                lines.append(line)
                line, x = [], 0.0
                tok = tok.lstrip()
                if not tok:
                    continue
                wsp = _width(tok, font, fs)
            line.append((x, tok, font, fs, color, url, size * 0.33 if sup else 0))
            x += wsp
        if line:
            lines.append(line)
        return lines

    def emit_lines(lines, x0, lead, bg=None, bar=None, pad=0.0):
        for ln in lines:
            ensure(lead)
            y = state["y"] - lead * 0.78
            if bg:
                r, g, b_ = _hex_rgb(bg)
                state["ops"].append(f"{r:.3f} {g:.3f} {b_:.3f} rg {x0 - pad:.2f} {state['y'] - lead:.2f} {TW - (x0 - M) - (x0 - M) + 2 * pad:.2f} {lead:.2f} re f".encode())
            if bar:
                r, g, b_ = _hex_rgb(bar)
                state["ops"].append(f"{r:.3f} {g:.3f} {b_:.3f} rg {x0 - pad - 3:.2f} {state['y'] - lead:.2f} 3 {lead:.2f} re f".encode())
            for x, tok, font, fs, color, url, rise in ln:
                r, g, b_ = _hex_rgb(color)
                state["ops"].append(
                    f"BT /{_FONT_RES[font]} {fs:.2f} Tf {r:.3f} {g:.3f} {b_:.3f} rg {x0 + x:.2f} {y + rise:.2f} Td ".encode()
                    + _pdf_str(tok) + b" Tj ET")
                if url:
                    w = _width(tok.rstrip(), font, fs)
                    state["annots"].append((x0 + x, y - 2, x0 + x + w, y + fs * 0.8, url))
            state["y"] -= lead

    def para(runs, size=11.5, lead=None, font_color=INK, x0=M, width=TW, before=0, after=6, bg=None, bar=None, pad=0.0, keep=False):
        lead = lead or size * 1.38
        lines = layout(runs, width, size, lead)
        need = lead * (len(lines) if keep else min(2, len(lines))) + before
        ensure(need)
        state["y"] -= before
        if bg and before == 0:
            pass
        emit_lines(lines, x0, lead, bg=bg, bar=bar, pad=pad)
        state["y"] -= after

    def runs_from(rs, base="rm", color=INK):
        out = []
        for r in rs:
            f = base
            if base in ("rm", "it", "bd", "bi"):
                f = {(False, False): "rm", (True, False): "bd", (False, True): "it", (True, True): "bi"}[(bool(r.get("b")), bool(r.get("i")))]
            elif r.get("b"):
                f = "sansb"
            out.append((r["text"], f, ACCENT if r.get("url") else color, r.get("url"), False))
        return out

    for b in blocks:
        t = b["t"]
        if t == "title":
            para([(b["text"], "sansb", ACCENT, None, False)], size=21, after=4)
        elif t == "subtitle":
            para([(b["text"], "it", MUTED, None, False)], size=13, after=6)
        elif t == "meta":
            para(runs_from(b["runs"], base="sans", color=MUTED), size=9, after=12)
        elif t == "epigraph":
            para([(b["text"], "it", MUTED, None, False)], size=11.5, x0=M + 30, width=TW - 60, before=4, after=2)
            para([(f"— {b['ref']} (KJV)", "rm", MUTED, None, False)], size=10.5, x0=M + 30, width=TW - 60, after=14)
        elif t == "h1":
            ensure(80)
            para([(b["text"], "sansb", ACCENT, None, False)], size=15, before=16, after=4)
            r, g, b_ = _hex_rgb(ACCENT)
            state["ops"].append(f"{r:.3f} {g:.3f} {b_:.3f} RG 0.8 w {M:.2f} {state['y'] + 2:.2f} m {PW - M:.2f} {state['y'] + 2:.2f} l S".encode())
            state["y"] -= 8
        elif t == "h2":
            ensure(110)
            para([(b["text"], "sansb", INK, None, False)], size=12.5, before=12, after=4, keep=True)
        elif t == "para":
            style = b.get("style")
            if style == "NewsLine":
                para(runs_from(b["runs"], base="sans"), size=10, after=6)
            elif style == "Closing":
                para(runs_from([dict(r, i=True) for r in b["runs"]]), size=11.5, before=4, after=8)
            else:
                para(runs_from(b["runs"]), size=11.5)
        elif t == "glance":
            for n, rs in b["items"]:
                lines = layout(runs_from(rs), TW - 22, 10.5, 14)
                ensure(14 * len(lines))
                y_top = state["y"]
                emit_lines([[(0, f"{n}.", "sansb", 10.5, ACCENT, None, 0)]], M, 14)
                state["y"] = y_top
                emit_lines(lines, M + 22, 14)
                state["y"] -= 2
            state["y"] -= 6
        elif t == "scripture":
            multi = len(b["verses"]) > 1
            rs = []
            for _, v, txt in b["verses"]:
                if multi:
                    rs.append((f"{v} ", "rm", ACCENT, None, True))
                rs.append((txt + " ", "it", INK, None, False))
            lead = 11.5 * 1.38
            lines = layout(rs, TW - 34, 11.5, lead)
            ref_lines = layout([(f"— {b['ref']}  ·  KJV  ·  {b['testament']}", "sansb", ACCENT, None, False)], TW - 34, 9.5, 14)
            ensure(4 + 5 + lead * len(lines) + 15 * len(ref_lines) + 5 + 2)
            state["y"] -= 4
            emit_lines([[]], M + 17, 5, bg=ACCENT_SOFT, bar=ACCENT, pad=10)
            emit_lines(lines, M + 17, lead, bg=ACCENT_SOFT, bar=ACCENT, pad=10)
            emit_lines(ref_lines, M + 17, 15, bg=ACCENT_SOFT, bar=ACCENT, pad=10)
            emit_lines([[]], M + 17, 5, bg=ACCENT_SOFT, bar=ACCENT, pad=10)
            state["y"] -= 10
        elif t == "prayer":
            first = True
            for ptxt in b["paras"]:
                rs = ([("Prayer: ", "bd", ACCENT, None, False)] if first else []) + [(ptxt, "rm", INK, None, False)]
                para(rs, size=11.5, after=8)
                first = False
        elif t == "rule":
            ensure(14)
            state["ops"].append(f"0.79 0.82 0.89 RG 0.5 w {M:.2f} {state['y'] - 6:.2f} m {PW - M:.2f} {state['y'] - 6:.2f} l S".encode())
            state["y"] -= 14

    # ---- serialise
    n = len(pages)
    objs = {}
    font_ids = {}
    next_id = [3]

    def alloc():
        i = next_id[0]
        next_id[0] += 1
        return i

    for key, base in _PDF_FONTS.items():
        fid = alloc()
        font_ids[key] = fid
        objs[fid] = f"<< /Type /Font /Subtype /Type1 /BaseFont /{base} /Encoding /WinAnsiEncoding >>".encode()
    font_dict = " ".join(f"/{_FONT_RES[k]} {v} 0 R" for k, v in font_ids.items())
    page_ids = []
    for idx, (ops, annots) in enumerate(pages):
        foot = f"{footer_text}  ·  Page {idx + 1} of {n}"
        fw = _width(foot, "sans", 8)
        r, g, b_ = _hex_rgb(MUTED)
        ops = ops + [f"BT /{_FONT_RES['sans']} 8 Tf {r:.3f} {g:.3f} {b_:.3f} rg {(PW - fw) / 2:.2f} {M / 2:.2f} Td ".encode() + _pdf_str(foot) + b" Tj ET"]
        stream = zlib.compress(b"\n".join(ops), 9)
        cid = alloc()
        objs[cid] = b"<< /Length " + str(len(stream)).encode() + b" /Filter /FlateDecode >>\nstream\n" + stream + b"\nendstream"
        annot_ids = []
        for (x1, y1, x2, y2, url) in annots:
            aid = alloc()
            u = url.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            objs[aid] = (f"<< /Type /Annot /Subtype /Link /Rect [{x1:.2f} {y1:.2f} {x2:.2f} {y2:.2f}] /Border [0 0 0] "
                         f"/A << /S /URI /URI ({u}) >> >>").encode("latin-1", errors="replace")
            annot_ids.append(aid)
        pid = alloc()
        page_ids.append(pid)
        annot_part = f" /Annots [{' '.join(f'{a} 0 R' for a in annot_ids)}]" if annot_ids else ""
        objs[pid] = (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PW} {PH}] /Resources << /Font << {font_dict} >> >> "
                     f"/Contents {cid} 0 R{annot_part} >>").encode()
    objs[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objs[2] = f"<< /Type /Pages /Kids [{' '.join(f'{p} 0 R' for p in page_ids)}] /Count {n} >>".encode()
    info_id = alloc()
    title_hex = ("FEFF" + title.encode("utf-16-be").hex().upper()).encode()
    objs[info_id] = b"<< /Title <" + title_hex + b"> /Producer (romans9ten11 build_prayer.py) >>"
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    for i in range(1, next_id[0]):
        offsets[i] = len(out)
        out += f"{i} 0 obj\n".encode() + objs[i] + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {next_id[0]}\n0000000000 65535 f \n".encode()
    for i in range(1, next_id[0]):
        out += f"{offsets[i]:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {next_id[0]} /Root 1 0 R /Info {info_id} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    with open(path, "wb") as fh:
        fh.write(out)
