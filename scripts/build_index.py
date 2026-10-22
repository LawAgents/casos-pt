"""Build indice.md (all works) and obras/<area>/indice.md for areas with more than 8 works.

Usage: python -I scripts/build_index.py [--repo DIR]
"""
import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, parse_front, work_files  # noqa: E402

AREA_THRESHOLD = 8
HEAD = "| Título | Autores | Ano | Área | Casos | Ficheiro |\n| --- | --- | ---: | --- | ---: | --- |"


def cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def rows(works, prefix=""):
    out = []
    for m in sorted(works, key=lambda m: (m["area"], -int(m["year"]), m["title"])):
        path = f"{prefix}obras/{m['area']}/{m['id']}.md"
        out.append(f"| {cell(m['title'])} | {cell(m['authors'])} | {m['year']} | {cell(m['area'])} | "
                   f"{m.get('cases', '')} | [{m['id']}.md]({path}) |")
    return out


def build(works):
    """Return {relative path: text} for the index files."""
    files = {}
    head = ["# Índice das obras", "",
            f"{len(works)} obras com casos práticos resolvidos. Texto sob as condições do CEJ: uso não comercial, "
            "citando a origem. Cada ficheiro traz a ligação para o PDF original.", "", HEAD]
    files["indice.md"] = "\n".join(head + rows(works)) + "\n"
    by_area = collections.defaultdict(list)
    for m in works:
        by_area[m["area"]].append(m)
    for area, ws in by_area.items():
        if len(ws) > AREA_THRESHOLD:
            lines = [f"# Índice: {area}", "", HEAD] + rows(ws, "../../")
            files[f"obras/{area}/indice.md"] = "\n".join(lines) + "\n"
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo")
    a = ap.parse_args()
    root = Path(a.repo) if a.repo else ROOT
    works = [parse_front(p.read_text(encoding="utf-8"))[0] for p in work_files(root)]
    for rel, text in build(works).items():
        (root / rel).write_text(text, encoding="utf-8", newline="\n")
        print("wrote", rel)


if __name__ == "__main__":
    main()
