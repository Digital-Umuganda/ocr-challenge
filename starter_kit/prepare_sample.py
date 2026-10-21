"""Convert the provided sample into the format evaluate.py expects.

    python prepare_sample.py --pdf sample.pdf --docx sample_ground_truth.docx --out sample/

Produces:
    sample/page_01.png, sample/page_02.png, ...   (200 DPI, RGB)
    sample/ground_truth.txt                        (all text from the .docx)
    sample/page_01.txt, sample/page_02.txt, ...   (per-page text, only if the .docx
                                                   has one manual page break per page)

Per-page text lets evaluate.py report WER/CER for each page. Word does not store
where pages end, so only manual page breaks (Ctrl+Enter) are used to split it.

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


def docx_to_pages(docx_path: Path) -> list[str]:
    """Text of the .docx in reading order, split at manual page breaks."""
    import docx
    from docx.oxml.ns import qn
    from docx.table import Table

    d = docx.Document(docx_path)
    pages, lines, line = [], [], ""

    def new_page():
        nonlocal lines
        pages.append("\n".join(lines).strip())
        lines = []

    for block in d.element.body.iterchildren():
        if block.tag == qn("w:p"):
            ppr = block.find(qn("w:pPr"))
            if ppr is not None and ppr.find(qn("w:pageBreakBefore")) is not None and lines:
                new_page()
            line = ""
            for el in block.iter(qn("w:t"), qn("w:tab"), qn("w:br")):
                if el.tag == qn("w:t"):
                    line += el.text or ""
                elif el.tag == qn("w:tab"):
                    line += "\t"
                elif el.get(qn("w:type")) == "page":  # manual page break inside the paragraph
                    lines.append(line)
                    line = ""
                    new_page()
                else:  # line break (Shift+Enter)
                    lines.append(line)
                    line = ""
            lines.append(line)
        elif block.tag == qn("w:tbl"):  # include table text, if any
            for row in Table(block, d).rows:
                lines.append(" ".join(cell.text for cell in row.cells))
    new_page()
    while len(pages) > 1 and not pages[-1]:  # a break at the very end adds no page
        pages.pop()
    return pages


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--docx", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("sample"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    n = pdf_to_pngs(args.pdf, args.out)
    pages = docx_to_pages(args.docx)
    (args.out / "ground_truth.txt").write_text("\n".join(pages).strip() + "\n", encoding="utf-8")
    for old in args.out.glob("page_*.txt"):  # stale per-page files would override ground_truth.txt
        old.unlink()
    print(f"Wrote {n} page image(s) and ground_truth.txt to {args.out}/")

    if len(pages) == n:
        for i, text in enumerate(pages, start=1):
            (args.out / f"page_{i:02d}.txt").write_text(text + "\n", encoding="utf-8")
        print(f"Wrote per-page ground truth page_01.txt ... page_{n:02d}.txt")
    elif n > 1:
        print(f"No per-page ground truth: the .docx splits into {len(pages)} part(s) at manual page "
              f"breaks but the PDF has {n} pages. Add a page break (Ctrl+Enter) after each page to get one.")


if __name__ == "__main__":
    main()
