"""Render every PDF page at 200 dpi to vmm_video/pages/page_N.png."""
import sys, os, fitz

pdf, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
doc = fitz.open(pdf)
for i, page in enumerate(doc, 1):
    pix = page.get_pixmap(dpi=200)
    p = os.path.join(out, f"page_{i}.png")
    pix.save(p)
    print(p, pix.width, pix.height)
