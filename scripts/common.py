"""Shared constants and helpers for the casos-pt scripts."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = Path(r"C:/Users/Admin/AppData/Local/Temp/claude/C--Users-Admin-Desktop-leis-pt/"
               r"fba6eb4c-e317-49f0-a3ce-abfe5b013c1b/scratchpad/casos-raw")
LICENCE = ("A reprodução total ou parcial dos seus conteúdos e textos está autorizada "
           "sempre que seja devidamente citada a respetiva origem.")
USE = "não comercial, citando a origem"
PUBLISHER = "Centro de Estudos Judiciários"
NOTICE = ("Texto extraído automaticamente de um PDF: confirma na fonte antes de citar. "
          "Doutrina e exercícios, não é lei.")
USER_AGENT = "LawAgents-casos-pt (github.com/LawAgents)"
FIELDS = ["id", "title", "authors", "year", "area", "publisher", "source", "page", "licenca",
          "uso", "text_version", "retrieved", "pages", "cases", "notice"]


def norm(text):
    """Collapse all whitespace (incl. non-breaking) to single spaces."""
    return re.sub(r"\s+", " ", text.replace("\u00a0", " ")).strip()


def load_works():
    return json.loads((ROOT / "config" / "obras.json").read_text(encoding="utf-8"))


def parse_front(text):
    """Parse the simple `key: value` front matter written by convert.py. Returns (dict, body)."""
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return None, text
    meta = {}
    for ln in text[4:end].splitlines():
        m = re.match(r"([a-z_]+):(?: (.*))?$", ln)
        if m:
            v = m.group(2) or ""
            if v.startswith('"') and v.endswith('"'):
                v = json.loads(v)
            meta[m.group(1)] = v
    return meta, text[end + 5:]


def work_files(root=None):
    """All obra files (not the per-area index files)."""
    root = Path(root) if root else ROOT
    return sorted(p for p in (root / "obras").glob("*/*.md") if p.name != "indice.md")


def count_headings(body):
    """Markdown headings in a body, ignoring fenced code."""
    n, fence = 0, False
    for ln in body.splitlines():
        if ln.startswith("```"):
            fence = not fence
        elif not fence and re.match(r"^#{1,6} \S", ln):
            n += 1
    return n
