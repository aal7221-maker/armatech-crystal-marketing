"""Crop machine photos + logo from the 200-dpi page renders, then build a contact sheet."""
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw, ImageFont

# rough search regions (x0, y0, x1, y1) in 200-dpi page pixels; left of the spec table, below the logo
JOBS = [
    ("ref_manual.png",   1, (0, 450, 560, 1400)),
    ("ref_semiauto.png", 2, (0, 360, 528, 1420)),
    ("ref_fullauto.png", 3, (0, 370, 582, 1460)),
    ("ref_cabinet.png",  4, (0, 380, 572, 1500)),
    ("ref_vms.png",      5, (0, 365, 605, 1510)),
    ("logo.png",         1, (0, 160, 420, 450)),
]
PAD = 24


def tighten(im, box, thr=232):
    reg = im.crop(box)
    a = np.asarray(reg.convert("L"))
    ys, xs = np.where(a < thr)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    bx, by = box[0], box[1]
    return (max(bx + x0 - PAD, 0), max(by + y0 - PAD, 0),
            min(bx + x1 + PAD, im.width), min(by + y1 + PAD, im.height))


def isolate_machine(im, box):
    """Keep only the largest connected object in box (the machine); white out the rest."""
    reg = np.asarray(im.crop(box)).astype(np.int16)
    gray = reg.mean(axis=2)
    sat = reg.max(axis=2) - reg.min(axis=2)
    fg = (gray < 225) | ((sat > 60) & (gray < 245))
    # break thin table lines / text from the machine: open, then close generously
    fg = ndimage.binary_opening(fg, iterations=2)
    blob = ndimage.binary_closing(fg, iterations=12)
    lab, n = ndimage.label(blob)
    sizes = ndimage.sum(blob, lab, range(1, n + 1))
    keep = lab == (int(np.argmax(sizes)) + 1)
    keep = ndimage.binary_fill_holes(keep)
    keep = ndimage.binary_dilation(keep, iterations=4)
    out = np.where(keep[..., None], reg, 255).astype(np.uint8)
    ys, xs = np.where(keep)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    c = Image.fromarray(out).crop((x0, y0, x1, y1))
    canvas = Image.new("RGB", (c.width + 2 * PAD, c.height + 2 * PAD), "white")
    canvas.paste(c, (PAD, PAD))
    return canvas, (box[0] + x0, box[1] + y0, box[0] + x1, box[1] + y1)


thumbs = []
for name, page, box in JOBS:
    im = Image.open(f"pages/page_{page}.png").convert("RGB")
    if name == "ref_vms.png":
        # white body on light background: plain crop, then erase the red page swoosh
        a = np.asarray(im.crop((0, 385, 600, 1510))).astype(np.int16)
        red = (a[..., 0] > 120) & (a[..., 0] - a[..., 1] > 70) & (a[..., 0] - a[..., 2] > 70)
        red = ndimage.binary_dilation(red, iterations=3)
        a[red] = 255
        crop = Image.fromarray(a.astype(np.uint8))
        crop.save(name)
        print(name, "page", page, "size", crop.size)
        thumbs.append((name, crop))
        continue
    if name.startswith("ref_"):
        crop, tb = isolate_machine(im, box)
        crop.save(name)
        print(name, "page", page, "box", tb, "size", crop.size)
        thumbs.append((name, crop))
        continue
    tb = tighten(im, box)
    crop = im.crop(tb)
    crop.save(name)
    print(name, "page", page, "box", tb, "size", crop.size)
    thumbs.append((name, crop))

# contact sheet: 3x2 grid of 420x420 cells
C, LBL = 420, 34
sheet = Image.new("RGB", (3 * C, 2 * (C + LBL)), (40, 40, 40))
d = ImageDraw.Draw(sheet)
try:
    f = ImageFont.truetype("arial.ttf", 22)
except OSError:
    f = ImageFont.load_default()
for k, (name, crop) in enumerate(thumbs):
    t = crop.copy(); t.thumbnail((C - 20, C - 20))
    cx, cy = (k % 3) * C, (k // 3) * (C + LBL)
    cell = Image.new("RGB", (C, C), "white"); cell.paste(t, ((C - t.width) // 2, (C - t.height) // 2))
    sheet.paste(cell, (cx, cy))
    d.text((cx + 10, cy + C + 5), f"{name}  {crop.width}x{crop.height}", fill="white", font=f)
sheet.save("contact_sheet.png")
print("contact_sheet.png", sheet.size)
