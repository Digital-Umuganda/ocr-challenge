"""Convert the provided sample into the format evaluate.py expects.

    python prepare_sample.py --pdf sample.pdf --docx sample_ground_truth.docx --out sample/

Produces:
    sample/page_01.png, sample/page_02.png, ...   (200 DPI, RGB)
    sample/ground_truth.txt                        (all text from the .docx)

Requires: pip install pymupdf python-docx
"""

import argparse
from pathlib import Path

DPI = 200  # Same resolution used for the hidden test pages.


def pdf_to_pngs(pdf_path: Path, out_dir: Path) -> int:
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    zoom = DPI / 72
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csRGB, alpha=False)
        pix.save(out_dir / f"page_{i:02d}.png")
    return len(doc)


def docx_to_text(docx_path: Path) -> str:
    import docx

    d = docx.Document(docx_path)
    lines = [p.text for p in d.paragraphs]
    for table in d.tables:  # include table text, if any
        for row in table.rows:
            lines.append(" ".join(cell.text for cell in row.cells))
    return "\n".join(lines).strip() + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--docx", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("sample"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    n = pdf_to_pngs(args.pdf, args.out)
    (args.out / "ground_truth.txt").write_text(docx_to_text(args.docx), encoding="utf-8")
    print(f"Wrote {n} page image(s) and ground_truth.txt to {args.out}/")


if __name__ == "__main__":
    main()
