"""Download the CEJ PDFs listed in config/obras.json to a raw folder OUTSIDE the repo.

Usage: python -I scripts/download.py [--raw DIR] [--only ID]

One request per second. Before a PDF is kept, the licence sentence must appear in its first
pages; if not, the work is aborted (file deleted) and reported. PDFs are never committed.
"""
import argparse
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import LICENCE, RAW_DIR, USER_AGENT, load_works, norm  # noqa: E402

FIRST_PAGES = 12


def licence_in_pdf(path):
    import pymupdf
    with pymupdf.open(path) as doc:
        text = norm(" ".join(doc[i].get_text() for i in range(min(FIRST_PAGES, len(doc)))))
    return norm(LICENCE) in text


def fetch(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    if not data.startswith(b"%PDF"):
        raise ValueError("response is not a PDF")
    dest.write_bytes(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(RAW_DIR))
    ap.add_argument("--only")
    a = ap.parse_args()
    raw = Path(a.raw)
    raw.mkdir(parents=True, exist_ok=True)
    failed = 0
    for w in load_works():
        if a.only and w["id"] != a.only:
            continue
        dest = raw / f"{w['id']}.pdf"
        time.sleep(1)  # 1 request per second
        try:
            fetch(w["source"], dest)
        except Exception as e:  # network or not a PDF
            print(f"ABORT {w['id']}: download failed ({e})")
            failed += 1
            continue
        if not licence_in_pdf(dest):
            dest.unlink()
            print(f"ABORT {w['id']}: licence sentence NOT found in the first {FIRST_PAGES} pages")
            failed += 1
            continue
        print(f"OK    {w['id']}: {dest.stat().st_size} bytes, licence sentence found")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
