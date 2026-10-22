"""Convert the CEJ PDFs to markdown, one file per work under obras/<area>/<id>.md.

Usage: python -I scripts/convert.py [--raw DIR] [--only ID] [--no-repair-glyphs]

Only reflow, no rewriting: lines are joined into paragraphs, running headers, footers and page
numbers are dropped, headings come from the PDF table of contents plus a few conservative
patterns (numbered headings, case and resolution markers). Text characters are copied as they
are in the PDF; broken ligature glyphs (fi, ti, fl... drawn as odd letters) are repaired by default (--no-repair-glyphs turns it off).
"""
import argparse
import collections
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (FIELDS, LICENCE, NOTICE, PUBLISHER, RAW_DIR, ROOT, USE, load_works,  # noqa: E402
                    norm)

# ---------------------------------------------------------------- patterns

# control characters (except tab and newline) are replaced by spaces
CTRL = {c: " " for c in [*range(0, 9), *range(11, 32), 127]}
TERMINAL = tuple(".:;?!)”»\"…]")
LIST_START = re.compile(
    r"^(?:[•▪●○◦]\s*|[-–—]\s+|\(?[ivx]{1,5}\)\s|\(?[a-z]\)\s|\d{1,2}\s?[.)–-]\s|"
    r"[IVX]{1,5}\s?[–.-]\s)", re.I)
BULLET_CHARS = "•▪●○◦"
NUMBERED = re.compile(r"^(?P<num>(?:\d{1,2}\.){1,4}\d{0,2}|\d{1,2}\s?[–-]|[IVX]{1,5}\s?[–.-])\s?\S")
SKIP_TOC = re.compile(r"^(capa|contracapa|cej|separador|isbn|[ií]ndice\d*)$", re.I)
JUNK_TOC = re.compile(r"_")

CASE = re.compile(
    r"^(caso\s+pr[áa]tico(\s*(n\.?\s*[º°o]?\s*)?\d+)?|caso\s+n\.?\s*[º°o]?\s*\d+|caso\s+\d+|"
    r"hip[óo]tese\s+\d+)\s*[:.]?(\s*[–-]\s*.{0,100})?$", re.I)
CASE_KEY = re.compile(r"^(caso\s+pr[áa]tico\s*(n\.?\s*[º°o]?\s*)?\d*|caso\s+n\.?\s*[º°o]?\s*\d+|caso\s+\d+|"
                      r"hip[óo]tese\s+\d+)", re.I)
SOLUTION = re.compile(r"^(solu[çc][ãa]o\s+do\s+caso\s+\d+|solu[çc][ãa]o\s+dos\s+casos\b.{0,120})\s*[:.]?$", re.I)
PART = re.compile(
    r"^(quest[õo]es|enunciado|resolu[çc][ãa]o|t[óo]picos\s+de\s+resolu[çc][ãa]o|"
    r"propostas?\s+de\s+(resolu[çc][ãa]o|solu[çc][ãa]o))\s*[:.]?$")
PART_LONG = re.compile(r"^QUEST[ÕO]ES\b.{0,200}$")  # "QUESTÕES [respondidas por ...]"

LIG = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl", "Ɵ": "ti", "ơ": "tí", "İ": "fí"}

# ---------------------------------------------------------------- pure helpers (unit tested)


def clean(text):
    """Normalise whitespace of one paragraph and drop control characters."""
    return norm(text.translate(CTRL))


def starts_item(text):
    return bool(LIST_START.match(text.strip()))


def join_lines(lines):
    """Join already-ordered text lines of ONE block into one string.

    A line that ends with a letter and a hyphen is joined to the next one without a space
    (the hyphens at line ends in these PDFs are real ones: Estados-Membros, jurídico-penais).
    """
    out = ""
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if not out:
            out = ln
        elif re.search(r"\w-$", out) and re.match(r"\w", ln):
            out += ln
        else:
            out += " " + ln
    return out


def reflow(lines, right=None):
    """Turn a list of line dicts {text, x0, x1} (reading order, one block or a page) into paragraphs.

    A new paragraph starts at an empty line, at a list marker, or after a short line that ends
    with sentence punctuation. `right` is the right margin (default: the largest x1 seen).
    """
    paras, cur, prev = [], [], None
    right = right if right is not None else max((ln.get("x1", 0) for ln in lines), default=0)
    left = min((ln.get("x0", 0) for ln in lines if ln["text"].strip()), default=0)
    for ln in lines:
        text = ln["text"].strip()
        if not text:
            if cur:
                paras.append(join_lines(cur))
            cur, prev = [], None
            continue
        if cur:
            short = prev is not None and prev.get("x1", right) < right - 30
            very_short = prev is not None and prev.get("x1", right) < left + 0.6 * (right - left)
            ended = prev["text"].rstrip().endswith(TERMINAL) or very_short
            indent = ln.get("x0", left) > left + 12
            if starts_item(text) or (short and ended) or (indent and ended):
                paras.append(join_lines(cur))
                cur = []
        cur.append(text)
        prev = ln
    if cur:
        paras.append(join_lines(cur))
    return [clean(p) for p in paras if clean(p)]


def classify_heading(text):
    """Return the kind of a case-related heading line, or None.

    case: a practical case ("CASO PRÁTICO 1", "Caso n.º 2", "Caso 3 – Cúmulo de penas", "Hipótese 1")
    solution: "Solução do caso 2"
    part: a labelled part of a case (QUESTÕES, ENUNCIADO, RESOLUÇÃO, TÓPICOS DE RESOLUÇÃO)
    Only whole short lines count, so running prose that starts with "Caso" is never a heading.
    """
    t = norm(text)
    if len(t) > 220:
        return None
    if CASE.match(t):
        return "case"
    if SOLUTION.match(t):
        return "solution"
    if PART.match(t.lower()) or PART_LONG.match(t):
        return "part"
    return None


def numbered_depth(text):
    """Depth of a numbered heading ("1." -> 1, "1.2." -> 2, "II –" -> 1), or 0 if not numbered.

    Long lines and plain "N –" lines that end with a full stop are article paragraphs, not headings.
    """
    t = norm(text)
    m = NUMBERED.match(t)
    if not m or len(t) > 200:
        return 0
    num = m.group("num")
    roman = bool(re.match(r"^[IVX]", num))
    dash = bool(re.match(r"^\d{1,2}\s?[–-]$", num))
    if (dash and (len(t) > 120 or t.endswith("."))) or t.endswith((";", ",")):
        return 0
    if roman or dash:
        return 1
    return len([p for p in num.split(".") if p]) or 1


def alnum(text, n=28):
    return re.sub(r"[^0-9a-zà-ÿ]", "", text.lower())[:n]


def toc_key(title):
    t = norm(title)
    t = re.sub(r"^(\d{1,2}\.\s*|[IVX]+\.\s*)", "", t)
    return alnum(t)


def toc_matches(title, para):
    """Does this paragraph carry the ToC entry's heading? By title prefix, or by the same leading number."""
    text = para["text"]
    k = toc_key(title)
    if k and alnum(re.sub(r"^(\d{1,2}\.\s*|[IVX]+\.\s*)", "", text)).startswith(k[:20]):
        return True
    n1 = re.match(r"^(\d{1,2}|[IVX]+)\.", norm(title))
    n2 = re.match(r"^(\d{1,2}|[IVX]+)\s?[.–-]", norm(text))
    return bool(n1 and n2 and n1.group(1) == n2.group(1) and len(text) <= 200 and len(para["lines"]) <= 3)


def repair(text):
    return "".join(LIG.get(c, c) for c in text)


# ---------------------------------------------------------------- PDF reading


def toc_entries(doc):
    """Usable ToC entries (level, title, page) and the set of pages to skip (covers, index, ISBN).

    Entries that are only file names ("Nota_inicial", "Ficha_tecnica1") are ignored: they are
    neither headings nor skipped pages.
    """
    toc = doc.get_toc()
    skip, keep = set(), []
    for i, (lvl, title, page) in enumerate(toc):
        title = norm(title)
        nxt = toc[i + 1][2] if i + 1 < len(toc) else None
        if SKIP_TOC.match(title):
            if title.lower() == "isbn":
                end = len(doc) + 1
            elif title.lower().startswith(("indice", "índice")) and nxt and nxt > page:
                end = nxt
            else:
                end = page + 1
            skip.update(range(page, end))
        elif not JUNK_TOC.search(title):
            keep.append((lvl, title, page))
    return keep, skip


def page_lines(page):
    """Flatten a page to line dicts in reading order with block id, size, bold, bbox."""
    out = []
    for bi, blk in enumerate(page.get_text("dict")["blocks"]):
        for ln in blk.get("lines", []):
            spans = ln["spans"]
            text = "".join(s["text"] for s in spans)
            nb = [s for s in spans if s["text"].strip()]
            out.append({
                "text": text, "block": bi,
                "x0": ln["bbox"][0], "x1": ln["bbox"][2], "y0": ln["bbox"][1], "y1": ln["bbox"][3],
                "size": max((s["size"] for s in nb), default=0.0),
                "bold": bool(nb) and all(s["flags"] & 16 for s in nb),
                "chars": sum(len(s["text"].strip()) for s in nb),
            })
    return out


def running_keys(doc, pages):
    """Texts that repeat in the top or bottom margin of >= 3 pages (running headers and footers)."""
    cnt = collections.Counter()
    for pno in pages:
        page = doc[pno - 1]
        h = page.rect.height
        seen = set()
        for ln in page_lines(page):
            if ln["y0"] < h * 0.09 or ln["y1"] > h * 0.93:
                k = re.sub(r"\d+", "#", norm(ln["text"]))
                if k and k not in seen:
                    seen.add(k)
                    cnt[k] += 1
    return {k for k, v in cnt.items() if v >= 3}


def is_running(ln, page_h, keys):
    t = norm(ln["text"])
    if not (ln["y0"] < page_h * 0.09 or ln["y1"] > page_h * 0.93):
        return False
    if re.fullmatch(r"\d{1,3}", t):
        return True
    if re.fullmatch(r"(\S ){3,}\S?", t + " "):  # letter-spaced footer "W O R K S H O P S"
        return True
    if classify_heading(t):
        return False
    return re.sub(r"\d+", "#", t) in keys


# ---------------------------------------------------------------- conversion


class Converter:
    def __init__(self, doc, work, repair_glyphs=False):
        self.doc, self.work, self.repair = doc, work, repair_glyphs
        self.toc, self.skip = toc_entries(doc)
        self.toc_by_page = collections.defaultdict(list)
        for e in self.toc:
            self.toc_by_page[e[2]].append(e)
        pages = [p for p in range(1, len(doc) + 1) if p not in self.skip]
        self.pages = pages
        self.keys = running_keys(doc, pages)
        self.out = []          # items: dict(kind, text, level)
        self.notes = []        # pending small-print paragraphs of the current page
        self.md_level = 1      # markdown level of the latest ToC heading
        self.case_open = None  # markdown level of the open case heading, if any
        self.section = 0
        self.cases = collections.OrderedDict()
        self.toc_headings = 0
        self.toc_unmatched = 0
        self.unmatched = []

    # ----- output helpers
    def flush_notes(self):
        for n in self.notes:
            self.out.append({"kind": "p", "text": n})
        self.notes = []

    def heading(self, text, level, role=None):
        self.flush_notes()
        level = max(2, min(6, level))
        self.out.append({"kind": "h", "text": clean(text), "level": level, "role": role,
                         "section": self.section})

    def settle(self):
        """A case heading directly followed by another case heading is a list of cases, not a case."""
        for a, b in zip(self.out, self.out[1:]):
            if a["kind"] == "h" and a["role"] == "case" and b["kind"] == "h" and b["role"] == "case":
                a["kind"], a["role"] = "p", None
        seen = set()
        for it in self.out:
            if it["kind"] == "h" and it["role"] == "case":
                m = CASE_KEY.match(norm(it["text"]))
                key = (it["section"], alnum(m.group(0), 40)) if m and re.search(r"\d", m.group(0)) else None
                if key is None or key not in seen:
                    self.cases[len(self.cases)] = it["text"]
                    seen.add(key)
        if not self.cases:  # Q&A book without case headings: count its distinct numbered questions
            for it in self.out:
                if it["kind"] == "h" and it["role"] == "question":
                    key = (it["section"], alnum(it["text"], 6))
                    if key not in seen:
                        self.cases[len(self.cases)] = it["text"]
                        seen.add(key)

    # ----- page processing
    def body_size(self, lines):
        c = collections.Counter()
        for ln in lines:
            c[round(ln["size"])] += ln["chars"]
        return c.most_common(1)[0][0] if c else 11

    def process_page(self, pno):
        page = self.doc[pno - 1]
        h = page.rect.height
        slide = page.rect.width > page.rect.height * 1.1
        lines = [ln for ln in page_lines(page) if not is_running(ln, h, self.keys)]
        if not any(ln["text"].strip() for ln in lines):  # e.g. a chapter divider that is only an image
            for e in self.toc_by_page.get(pno, []):
                self.toc_unmatched += 1
                self.unmatched.append(e[1])
                self.open_section(e)
                self.heading(e[1], self.md_level)
            return
        body = self.body_size(lines)
        # trailing small print (footnotes) is held back until the next page's first paragraph
        last_body_y = max((ln["y0"] for ln in lines if ln["size"] >= body - 0.9 and ln["text"].strip()),
                          default=0)
        main, tail = [], []
        for ln in lines:
            small = ln["size"] < body - 0.9 and ln["size"] > 0
            (tail if (small and ln["y0"] > last_body_y and not slide) else main).append(ln)
        bold_share = sum(ln["chars"] for ln in main if ln["bold"]) / max(1, sum(ln["chars"] for ln in main))
        right = max((ln["x1"] for ln in main if ln["text"].strip()), default=0)

        paras = self.paragraphs(main, right, slide)
        toc_todo = list(self.toc_by_page.get(pno, []))
        match = {}
        for i, p in enumerate(paras):
            for e in toc_todo:
                if toc_matches(e[1], p):
                    match[i] = e
                    toc_todo.remove(e)
                    break
        for e in toc_todo:  # ToC entry whose title was not found on its page: heading at page start
            self.toc_unmatched += 1
            self.unmatched.append(e[1])
            self.open_section(e)
            self.heading(e[1], self.md_level)
        first_body = True
        for i, p in enumerate(paras):
            text = p["text"]
            consumed = False
            if i in match:
                self.open_section(match[i])
                self.heading(text, self.md_level)
                consumed = True
            if consumed:
                first_body = False
                continue
            if not slide and p["size"] >= body - 0.6:
                kind = classify_heading(text)
                if kind == "case":
                    self.case_open = self.md_level + 1
                    self.heading(text, self.case_open, "case")
                    first_body = False
                    continue
                if kind == "solution":
                    self.heading(text, self.md_level + 1)
                    first_body = False
                    continue
                if kind == "part":
                    self.heading(text, (self.case_open or self.md_level) + 1)
                    first_body = False
                    continue
                d = numbered_depth(text)
                if re.match(r"^\d{1,2}\.\s", text) and text.endswith("?") and len(text) <= 700:
                    self.heading(text, self.md_level + 1, "question")  # numbered practical question
                    first_body = False
                    continue
                if d and p["bold"] and bold_share < 0.6 and len(p["lines"]) <= 3:
                    self.case_open = None
                    level = (self.md_level if self.toc else 1) + d
                    if not self.toc and d == 1:  # no usable ToC: top-level numbered headings define the sections
                        self.section += 1
                        self.md_level = min(6, level)
                    self.heading(text, level)
                    first_body = False
                    continue
            if first_body and self.try_continue(text, slide):
                first_body = False
                continue
            first_body = False
            self.flush_notes()
            self.out.append({"kind": "p", "text": text})
        # small print goes after the page body
        for p in self.paragraphs(tail, right, False):
            self.notes.append(p["text"])

    def open_section(self, entry):
        self.toc_headings += 1
        self.section += 1
        self.md_level, self.case_open = entry[0] + 1, None

    def try_continue(self, text, slide):
        """First paragraph of a page that continues the last paragraph of the previous page."""
        if slide or not self.out or self.out[-1]["kind"] != "p":
            return False
        prev = self.out[-1]["text"]
        if prev.endswith(TERMINAL) or not text[:1].islower() or starts_item(text):
            return False
        sep = "" if re.search(r"\w-$", prev) and re.match(r"\w", text) else " "
        self.out[-1]["text"] = prev + sep + text
        self.flush_notes()
        return True

    def paragraphs(self, lines, right, slide):
        res = []
        if slide:  # slides pasted into the book: keep one paragraph per line, no joining
            for ln in lines:
                if ln["text"].strip():
                    res.append({"text": clean(ln["text"]), "size": ln["size"], "bold": ln["bold"], "lines": [ln]})
            return res
        blocks = collections.OrderedDict()
        for ln in lines:
            blocks.setdefault(ln["block"], []).append(ln)
        for blk in blocks.values():
            for grp in group_by_reflow(blk, right):
                sizes = [ln["size"] for ln in grp["lines"] if ln["text"].strip()]
                res.append({"text": grp["text"], "size": max(sizes, default=0), "lines": grp["lines"],
                            "bold": all(ln["bold"] for ln in grp["lines"] if ln["text"].strip())})
        return res

    def run(self):
        for pno in self.pages:
            self.process_page(pno)
        self.flush_notes()
        self.settle()
        return self.markdown()

    def markdown(self):
        parts = [f"# {self.work['title']}"]
        for it in self.out:
            t = it["text"]
            if self.repair:
                t = repair(t)
            if it["kind"] == "p":
                if t and t[0] in BULLET_CHARS:
                    t = "- " + t[1:].lstrip()
                parts.append(t)
            else:
                parts.append("#" * it["level"] + " " + t)
        return "\n\n".join(parts) + "\n"

    @property
    def headings(self):
        return 1 + sum(1 for it in self.out if it["kind"] == "h")


def group_by_reflow(blk, right):
    """Reflow one block; return [{text, lines}] where lines are the source lines of each paragraph."""
    texts = reflow(blk, right)
    # map each paragraph back to its source lines (for size/bold): consume lines in order
    groups, idx = [], 0
    for para in texts:
        want = alnum(para, 10**6)
        acc, got = [], ""
        while idx < len(blk) and len(got) < len(want):
            acc.append(blk[idx])
            got += alnum(blk[idx]["text"], 10**6)
            idx += 1
        groups.append({"text": para, "lines": acc or blk[:1]})
    return groups


# ---------------------------------------------------------------- front matter and driver


def front_matter(work, doc, conv, today):
    pages = len(doc)
    cases = len(conv.cases) if conv.cases else None
    vals = {
        "id": work["id"], "title": work["title"], "authors": work["authors"], "year": work["year"],
        "area": work["area"], "publisher": PUBLISHER, "source": work["source"], "page": work["page"],
        "licenca": LICENCE, "uso": USE, "text_version": "extraído do PDF", "retrieved": today,
        "pages": pages, "cases": cases, "notice": NOTICE,
    }
    blank = [n for n in range(1, pages + 1) if n not in conv.skip and len(doc[n - 1].get_text().strip()) < 30]
    lines = ["---"]
    for k in FIELDS:
        v = vals[k]
        if v is None:
            lines.append(f"{k}:")
        elif isinstance(v, int):
            lines.append(f"{k}: {v}")
        else:
            lines.append(f"{k}: " + json.dumps(v, ensure_ascii=False))
    lines.append(f"headings: {conv.headings}")
    lines.append(f"pages_without_text: {len(blank)}")
    lines.append(f"toc_entries: {len(conv.toc)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def main():
    import pymupdf
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(RAW_DIR))
    ap.add_argument("--only")
    ap.add_argument("--repair-glyphs", action=argparse.BooleanOptionalAction, default=True)
    a = ap.parse_args()
    today = date.today().isoformat()
    for w in load_works():
        if a.only and w["id"] != a.only:
            continue
        pdf = Path(a.raw) / f"{w['id']}.pdf"
        if not pdf.exists():
            print(f"SKIP {w['id']}: PDF not downloaded")
            continue
        doc = pymupdf.open(pdf)
        conv = Converter(doc, w, a.repair_glyphs)
        body = conv.run()
        dest = ROOT / "obras" / w["area"] / f"{w['id']}.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(front_matter(w, doc, conv, today) + body, encoding="utf-8", newline="\n")
        print(f"{w['id']}: pages={len(doc)} headings={conv.headings} toc={len(conv.toc)} "
              f"toc_unmatched={conv.toc_unmatched} cases={len(conv.cases)}")
        for t in conv.unmatched:
            print(f"    ToC entry without a matching line on its page (heading taken from the ToC): {t[:80]}")


if __name__ == "__main__":
    main()
