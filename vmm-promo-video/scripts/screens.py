"""Procedural measurement-software screens (modelled on the real Crystal VMM software in the operation video).

screen_thread(t, n)  thread-profile edge scan, pitch + flank angle
screen_holes(t, n)   hole-plate circle detection with diameters + OK tags
screen_report(t, n)  inspection report sliding in
All return a 1280x720 RGB PIL image. t = local frame, n = segment length in frames.
Values are illustrative demo measurements, not product specs.
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 720
LIME = (92, 238, 52)
DARK = (14, 16, 18)
PANEL = (28, 31, 35)
PANEL2 = (38, 42, 47)
LINE = (70, 76, 84)
WHITE = (240, 244, 246)
GREY = (150, 158, 166)
RED = (232, 40, 44)
CYAN = (40, 210, 255)
OKGREEN = (60, 255, 120)
F_BLACK = r"C:\Windows\Fonts\seguibl.ttf"
F_SEMI = r"C:\Windows\Fonts\seguisb.ttf"
F_MONO = r"C:\Windows\Fonts\consolab.ttf"


def F(p, s):
    try:
        return ImageFont.truetype(p, s)
    except OSError:
        return ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", s)


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


# camera viewport inside the UI
VX0, VY0, VX1, VY1 = 40, 70, 860, 560
VW, VH = VX1 - VX0, VY1 - VY0


def ui_frame(title, t, n, dro):
    """Dark software chrome + right panel with live DRO."""
    im = Image.new("RGB", (W, H), DARK)
    d = ImageDraw.Draw(im)
    # top bar
    d.rectangle((0, 0, W, 50), fill=PANEL)
    for k in range(9):
        d.rounded_rectangle((20 + k * 34, 14, 44 + k * 34, 36), 4, fill=PANEL2)
    d.text((360, 13), title, font=F(F_SEMI, 18), fill=GREY)
    d.ellipse((W - 40, 17, W - 24, 33), fill=RED)
    # viewport border
    d.rectangle((VX0 - 2, VY0 - 2, VX1 + 1, VY1 + 1), outline=LINE, width=2)
    # right panel
    d.rectangle((890, 70, W - 30, VY1), fill=PANEL)
    d.text((910, 84), "DRO", font=F(F_BLACK, 20), fill=WHITE)
    fm = F(F_MONO, 30)
    for k, (ax, val) in enumerate(zip("XYZ", dro)):
        y = 124 + k * 58
        d.rounded_rectangle((910, y, W - 50, y + 46), 6, fill=(10, 12, 14))
        d.text((924, y + 7), ax, font=F(F_BLACK, 24), fill=CYAN)
        txt = f"{val:+9.4f}"
        d.text((W - 62 - fm.getlength(txt), y + 6), txt, font=fm, fill=(255, 214, 60))
    # bottom strip
    d.rectangle((40, 580, W - 30, 690), fill=PANEL)
    return im, d


def dro_at(t, base, drift):
    return [b + dr * math.sin(t / 9 + k) * 0.5 + dr * t / 60 for k, (b, dr) in enumerate(zip(base, drift))]


def result_rows(d, rows, t0, t, x=910, y=310):
    fl, fv = F(F_SEMI, 17), F(F_MONO, 22)
    d.text((x, y - 4), "RESULTS", font=F(F_BLACK, 18), fill=WHITE)
    for k, (lbl, val, ok) in enumerate(rows):
        a = ease((t - t0 - k * 6) / 6)
        if a <= 0:
            continue
        yy = y + 30 + k * 44
        col = tuple(int(c * a + 28 * (1 - a)) for c in WHITE)
        d.text((x, yy), lbl, font=fl, fill=GREY)
        d.text((x + 120, yy - 3), val, font=fv, fill=col)
        if ok:
            d.rounded_rectangle((W - 92, yy - 2, W - 50, yy + 22), 5, fill=(20, 90, 40))
            d.text((W - 84, yy - 1), "OK", font=F(F_BLACK, 16), fill=OKGREEN)


def label(d, x, y, txt, col=WHITE):
    f = F(F_MONO, 18)
    w = f.getlength(txt)
    d.rectangle((x - 6, y - 3, x + w + 6, y + 23), fill=(255, 255, 255))
    d.text((x, y), txt, font=f, fill=(10, 10, 10))


# ---------------------------------------------------------------- thread profile
def screen_thread(t, n):
    im, d = ui_frame("Profile measurement  ·  Thread M10 × 1.5", t, n, dro_at(t, (12.4815, -3.2207, 41.0062), (0.02, 0.0, 0.0)))
    vp = Image.new("RGB", (VW, VH), LIME)
    vd = ImageDraw.Draw(vp)
    pitch = 118            # px per pitch in the viewport
    off = -t * 0.8         # slow stage drift
    # black thread silhouette: band in the middle with 60° teeth top and bottom
    depth = (pitch / 2) / math.tan(math.radians(30))     # true 60° flanks
    top_root, bot_root = 160, 330
    top_crest, bot_crest = top_root - depth, bot_root + depth
    pts_top, pts_bot = [], []
    x = off - pitch
    while x < VW + pitch:
        pts_top += [(x, top_root), (x + pitch * 0.5, top_crest)]
        pts_bot += [(x, bot_root), (x + pitch * 0.5, bot_crest)]
        x += pitch
    poly = pts_top + [(VW + pitch, top_root), (VW + pitch, bot_root)] + pts_bot[::-1]
    poly = [(p[0], p[1]) for p in pts_top] + [(p[0], p[1]) for p in reversed(pts_bot)]
    vd.polygon(poly, fill=(22, 22, 22))
    # red crosshair
    vd.line((0, VH // 2, VW, VH // 2), fill=RED, width=1)
    vd.line((VW // 2, 0, VW // 2, VH), fill=RED, width=1)
    # edge scan sweep: highlight detected edge points left of the scan line
    sx = int(ease(t / (n * 0.45)) * VW)
    if sx < VW:
        vd.line((sx, 0, sx, VH), fill=CYAN, width=2)
    for k in range(0, len(pts_top) - 1):
        (x0, y0), (x1, y1) = pts_top[k], pts_top[k + 1]
        for s in np.linspace(0, 1, 6):
            px, py = x0 + (x1 - x0) * s, y0 + (y1 - y0) * s
            if 0 < px < min(sx, VW):
                vd.ellipse((px - 2.5, py - 2.5, px + 2.5, py + 2.5), fill=CYAN)
    im.paste(vp, (VX0, VY0))
    # dimension overlays once the scan passes
    a = (t - n * 0.45) / 8
    if a > 0:
        # pitch dimension between two crests
        cx = [p[0] for p in pts_top[1::2] if 200 < p[0] < VW - 150][:2]
        if len(cx) == 2:
            y = VY0 + top_crest - 28
            d.line((VX0 + cx[0], y, VX0 + cx[1], y), fill=WHITE, width=2)
            for c in cx:
                d.line((VX0 + c, y - 8, VX0 + c, y + 30), fill=WHITE, width=1)
            label(d, VX0 + (cx[0] + cx[1]) / 2 - 60, y - 34, "P 1.5003 mm")
        # flank angle arc on a bottom tooth
        if a > 0.6:
            # 60° arc in the green notch above a root (apex at top_root)
            rx = [p[0] for p in pts_top[0::2] if 420 < p[0] < VW - 150][0]
            cxp, cyp = VX0 + rx, VY0 + top_root
            r = 64
            d.arc((cxp - r, cyp - r, cxp + r, cyp + r), 240, 300, fill=WHITE, width=3)
            for ang in (240, 300):
                ex, ey = cxp + (r + 18) * math.cos(math.radians(ang)), cyp + (r + 18) * math.sin(math.radians(ang))
                d.line((cxp, cyp, ex, ey), fill=WHITE, width=1)
            label(d, cxp - 62, cyp - r - 52, "FLANK 60.02°")
    result_rows(d, [("Pitch", "1.5003", True), ("Flank", "60.02°", True), ("Major Ø", "9.976", True)], int(n * 0.5), t)
    _bottom(d, t, "Edge points: %d" % min(240, int(t * 5)))
    return im


# ---------------------------------------------------------------- hole plate
HOLES = [(150, 150, 34), (300, 150, 40), (450, 150, 46), (600, 150, 52),
         (150, 330, 34), (300, 330, 40), (450, 330, 46), (600, 330, 52)]
DIAS = ["Ø 6.012", "Ø 7.008", "Ø 8.004", "Ø 9.011", "Ø 6.009", "Ø 7.013", "Ø 8.006", "Ø 9.002"]


def screen_holes(t, n):
    im, d = ui_frame("Feature measurement  ·  Hole plate", t, n, dro_at(t, (-10.5140, 2.0610, 38.4417), (0.0, 0.01, 0.0)))
    vp = Image.new("RGB", (VW, VH), LIME)
    vd = ImageDraw.Draw(vp)
    for (x, y, r) in HOLES:
        vd.ellipse((x - r, y - r, x + r, y + r), fill=(22, 22, 22))
    im.paste(vp, (VX0, VY0))
    step = max(3, int(n * 0.65 / len(HOLES)))
    for k, ((x, y, r), dia) in enumerate(zip(HOLES, DIAS)):
        lt = (t - 4 - k * step) / 6
        if lt <= 0:
            continue
        a = ease(lt)
        X, Y = VX0 + x, VY0 + y
        rr = r + 14 * (1 - a)
        d.ellipse((X - rr, Y - rr, X + rr, Y + rr), outline=RED, width=3)
        d.line((X - r - 10, Y, X + r + 10, Y), fill=RED, width=1)
        d.line((X, Y - r - 10, X, Y + r + 10), fill=RED, width=1)
        if a > 0.7:
            label(d, X - 38, Y + r + 10, dia)
    done = sum(1 for k in range(len(HOLES)) if t - 4 - k * step > 6)
    result_rows(d, [("Holes", f"{done}/8", done == 8), ("Pitch X", "150.002", True), ("Pos. tol", "±0.010", True)],
                int(n * 0.55), t)
    _bottom(d, t, f"Circles detected: {done}")
    return im


# ---------------------------------------------------------------- report
def screen_report(t, n):
    im = screen_holes(n - 1, n)                 # last state behind
    im = Image.blend(im, Image.new("RGB", (W, H), (0, 0, 0)), 0.45)
    s = ease(t / 9)
    sheet = Image.new("RGB", (760, 560), (250, 251, 252))
    sd = ImageDraw.Draw(sheet)
    sd.rectangle((0, 0, 760, 56), fill=(30, 34, 38))
    sd.text((24, 12), "INSPECTION REPORT", font=F(F_BLACK, 26), fill=WHITE)
    sd.text((470, 18), "Part: HOLE PLATE-12", font=F(F_SEMI, 17), fill=(200, 205, 210))
    hdr = ["#", "Feature", "Nominal", "Measured", "Dev.", "Result"]
    xs = [24, 70, 250, 380, 520, 640]
    fh, fr = F(F_SEMI, 17), F(F_MONO, 19)
    for x, h in zip(xs, hdr):
        sd.text((x, 76), h, font=fh, fill=(90, 96, 104))
    sd.line((20, 104, 740, 104), fill=(200, 204, 208), width=2)
    noms = ["6.000", "7.000", "8.000", "9.000", "6.000", "7.000", "8.000", "9.000"]
    for k in range(8):
        a = ease((t - 6 - k * 2) / 4)
        if a <= 0:
            continue
        y = 116 + k * 50
        meas = DIAS[k].split()[1]
        dev = float(meas) - float(noms[k])
        c = tuple(int(30 + (1 - a) * 200) for _ in range(3))
        row = [str(k + 1), f"Circle Ø", noms[k], meas, f"{dev:+.3f}"]
        for x, v in zip(xs, row):
            sd.text((x, y), v, font=fr, fill=c)
        sd.rounded_rectangle((640, y - 2, 700, y + 26), 6, fill=(28, 150, 70))
        sd.text((656, y + 1), "OK", font=F(F_BLACK, 17), fill=(255, 255, 255))
        sd.line((20, y + 38, 740, y + 38), fill=(232, 234, 236), width=1)
    sh = sheet.resize((int(760 * (0.9 + 0.1 * s)), int(560 * (0.9 + 0.1 * s))), Image.LANCZOS)
    x = (W - sh.width) // 2
    y = int(H + 40 - (H + 40 - (H - sh.height) // 2) * s)
    shadow = Image.new("RGBA", (sh.width + 60, sh.height + 60), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle((30, 30, sh.width + 30, sh.height + 30), fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    im = im.convert("RGBA")
    im.alpha_composite(shadow, (x - 30, y - 18))
    im = im.convert("RGB")
    im.paste(sh, (x, y))
    return im


def _bottom(d, t, status):
    d.text((60, 596), status, font=F(F_SEMI, 18), fill=GREY)
    # mini magnification / light indicators
    d.text((60, 630), "MAG 120X   ·   CONTOUR LIGHT 68%   ·   RING LIGHT 8-ZONE", font=F(F_SEMI, 16), fill=(110, 118, 126))
    blink = (t // 8) % 2 == 0
    d.ellipse((W - 80, 610, W - 64, 626), fill=OKGREEN if blink else (30, 80, 40))


if __name__ == "__main__":
    import os
    os.makedirs("v3/preview", exist_ok=True)
    screen_thread(70, 90).save("v3/preview/scr_thread.png")
    screen_holes(70, 75).save("v3/preview/scr_holes.png")
    screen_report(40, 45).save("v3/preview/scr_report.png")
    print("ok")
