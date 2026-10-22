"""Validate the obras files. Exit code 1 if anything is wrong.

Usage: python -I scripts/validate.py [--repo DIR]

Checks per file: all front-matter fields, the literal licence sentence and use, a source link,
a non-empty body, id equal to the file name and unique, area equal to the folder, and the number
of headings against the front matter and the expected ToC entries.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FIELDS, LICENCE, NOTICE, USE, count_headings, parse_front, work_files  # noqa: E402

MIN_BODY = 1000


def check_text(path, text):
    """Return the list of problems of one obra file."""
    path = Path(path)
    meta, body = parse_front(text)
    if meta is None:
        return ["no front matter"]
    errs = [f"missing field: {k}" for k in FIELDS if k not in meta]
    for k in FIELDS:
        if k in meta and k != "cases" and not str(meta[k]).strip():
            errs.append(f"empty field: {k}")
    if meta.get("licenca") != LICENCE:
        errs.append("licence sentence missing or not literal in front matter")
    if meta.get("uso") != USE:
        errs.append("uso is not the required text")
    if meta.get("notice") != NOTICE:
        errs.append("notice is not the required text")
    if not str(meta.get("source", "")).startswith("http"):
        errs.append("no source link")
    if not str(meta.get("page", "")).startswith("http"):
        errs.append("no page link")
    if len(body.strip()) < MIN_BODY:
        errs.append("body is empty or too short")
    if meta.get("id") != path.stem:
        errs.append("id differs from the file name")
    if path.parent.name != meta.get("area"):
        errs.append("area differs from the folder")
    for k in ("year", "pages", "headings", "toc_entries"):
        if k in meta and not str(meta[k]).isdigit():
            errs.append(f"{k} is not an integer")
    if str(meta.get("cases", "")) and not str(meta["cases"]).isdigit():
        errs.append("cases is neither empty nor an integer")
    if str(meta.get("headings", "")).isdigit() and str(meta.get("toc_entries", "")).isdigit():
        found = count_headings(body)
        if found != int(meta["headings"]):
            errs.append(f"headings in the body ({found}) differ from the front matter ({meta['headings']})")
        if found - 1 < int(meta["toc_entries"]):  # minus the title
            errs.append(f"fewer headings ({found - 1}) than ToC entries ({meta['toc_entries']})")
    return errs


def check_all(root=None):
    problems, ids = {}, {}
    for p in work_files(root):
        text = p.read_text(encoding="utf-8")
        errs = check_text(p, text)
        meta, _ = parse_front(text)
        wid = (meta or {}).get("id")
        if wid in ids:
            errs.append(f"duplicate id (also in {ids[wid]})")
        ids.setdefault(wid, p.name)
        if errs:
            problems[str(p)] = errs
    return problems, len(ids)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo")
    a = ap.parse_args()
    problems, n = check_all(a.repo)
    if n == 0:
        problems["obras"] = ["no obra files found"]
    for f, errs in problems.items():
        for e in errs:
            print(f"FAIL {f}: {e}")
    print(f"{n} files checked, {sum(len(v) for v in problems.values())} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
