"""Resolution-independent renderer for the v5 promo (same layout as VMM_promo_v5_720p).

Layout is authored in logical 1280x720 coordinates and scaled by S to the output size,
so text, UI, callouts and the logo are drawn natively at 1080p (S=1.5).

python edit_hd.py preview f1 f2 ...      -> v5hd/preview/hd_XXXX.png
python edit_hd.py render [out.mp4]       -> VMM_promo_v5_1080p.mp4
Env: VMM_OUT_H (default 1080)
"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import logo_anim as LA

FF = r"C:\Users\lunaw\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
LW, LH, FPS = 1280, 720, 30                    # logical design space
PH = int(os.environ.get("VMM_OUT_H", "1080"))
S = PH / LH
PW = int(round(LW * S))
SEGDIR = "v5hd/seg"

GREEN, RED, GREY = (60, 255, 120), (225, 30, 36), (176, 184, 190)
WHITE = (240, 244, 246)
F_BLACK = r"C:\Windows\Fonts\seguibl.ttf"
F_BOLD = r"C:\Windows\Fonts\segoeuib.ttf"
F_SEMI = r"C:\Windows\Fonts\seguisb.ttf"
F_MONO = r"C:\Windows\Fonts\consolab.ttf"


# ================================================================ scaling helpers
def F(path, size):
    return ImageFont.truetype(path, max(1, int(round(size * S))))


def Lw(font, txt):
    """text width in logical px"""
    return font.getlength(txt) / S


def P(v):
    return int(round(v * S))


class SD:
    """ImageDraw wrapper: logical coords/widths/radii -> physical."""
    def __init__(self, img):
        self.d = ImageDraw.Draw(img)

    @staticmethod
    def _xy(xy):
        if isinstance(xy[0], (tuple, list)):
            return [(x * S, y * S) for x, y in xy]
        return [v * S for v in xy]

    def text(self, xy, txt, font, fill):
        self.d.text((xy[0] * S, xy[1] * S), txt, font=font, fill=fill)

    def rectangle(self, box, fill=None, outline=None, width=1):
        self.d.rectangle(self._xy(box), fill=fill, outline=outline, width=max(1, P(width)))

    def rounded_rectangle(self, box, r, fill=None, outline=None, width=1):
        self.d.rounded_rectangle(self._xy(box), r * S, fill=fill, outline=outline, width=max(1, P(width)))

    def line(self, xy, fill, width=1):
        self.d.line(self._xy(xy), fill=fill, width=max(1, P(width)))

    def ellipse(self, box, fill=None, outline=None, width=1):
        self.d.ellipse(self._xy(box), fill=fill, outline=outline, width=max(1, P(width)))

    def arc(self, box, a0, a1, fill, width=1):
        self.d.arc(self._xy(box), a0, a1, fill=fill, width=max(1, P(width)))

    def polygon(self, pts, fill):
        self.d.polygon(self._xy(pts), fill=fill)


def new(mode="RGBA", size=None, color=(0, 0, 0, 0)):
    return Image.new(mode, size or (PW, PH), color)


def ease_out(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def back_out(t, s=1.9):
    t = min(max(t, 0.0), 1.0) - 1
    return t * t * ((s + 1) * t + s) + 1


def text_img(txt, fnt, fill, glow=None):
    l, t, r, b = fnt.getbbox(txt)
    pad = P(30) if glow else P(4)
    im = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - l, pad - t), txt, font=fnt, fill=fill)
    if glow:
        g = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).text((pad - l, pad - t), txt, font=fnt, fill=glow)
        g = g.filter(ImageFilter.GaussianBlur(14 * S))
        im = Image.alpha_composite(Image.alpha_composite(g, g), im)
    return im


def paste(base, sprite, x, y, alpha=1.0, scale=1.0, anchor="lt"):
    """x, y logical; sprite physical."""
    if alpha <= 0.003:
        return
    sp = sprite
    if abs(scale - 1.0) > 1e-3:
        sp = sp.resize((max(1, int(sp.width * scale)), max(1, int(sp.height * scale))), Image.LANCZOS)
    if alpha < 1.0:
        a = sp.getchannel("A").point(lambda v: int(v * alpha))
        sp = sp.copy(); sp.putalpha(a)
    X, Y = x * S, y * S
    if anchor == "mm":
        X, Y = X - sp.width / 2, Y - sp.height / 2
    base.alpha_composite(sp, (int(round(X)), int(round(Y))))


def grid_xy():
    yy, xx = np.mgrid[0:PH, 0:PW].astype(np.float32)
    return xx / S, yy / S, xx, yy


# ================================================================ video sources
class Reader:
    def __init__(self, path):
        self.path, self.proc, self.pos, self._last = path, None, 0, None

    def _open(self, start):
        if self.proc:
            self.proc.kill()
        self.proc = subprocess.Popen(
            [FF, "-v", "quiet", "-ss", f"{start / FPS:.4f}", "-i", self.path, "-vf", f"scale={PW}:{PH}:flags=lanczos",
             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.pos = start

    def frame(self, idx):
        if self.proc is not None and idx == self.pos - 1 and self._last is not None:
            return self._last
        if self.proc is None or idx < self.pos:
            self._open(idx)
        while self.pos <= idx:
            buf = self.proc.stdout.read(PW * PH * 3)
            if len(buf) < PW * PH * 3:
                return self._last if self._last is not None else np.zeros((PH, PW, 3), np.uint8)
            self._last = np.frombuffer(buf, np.uint8).reshape(PH, PW, 3)
            self.pos += 1
        return self._last


READERS = {}


SRC_FILE = {"opener": "opener_logo"}      # opener with the tracked Crystal badge on the camera head


def vframe(name, t):
    p = f"{SEGDIR}/{SRC_FILE.get(name, name)}.mp4"
    if p not in READERS:
        READERS[p] = Reader(p)
    return READERS[p].frame(t)


# ================================================================ opener: hook + title
F_HOOK = F(F_BLACK, 118)
HOOK_SPR = [(text_img("MEASURE", F_HOOK, (255, 255, 255)), 8),
            (text_img("TO THE", F_HOOK, (255, 255, 255)), 24),
            (text_img("MICRON.", F_HOOK, GREEN, (60, 255, 120, 200)), 40)]
HERO = None


def hero_title(base, t):
    global HERO
    if HERO is None:
        X, Y, _, _ = grid_xy()
        a = np.clip((Y - 330) / 390, 0, 1) * np.clip(1.25 - X / 1000, 0, 1) * 230
        g = np.zeros((PH, PW, 4), np.uint8); g[..., 3] = a.astype(np.uint8)
        HERO = (Image.fromarray(g, "RGBA"),
                text_img("C R Y S T A L   ·   S I N C E   1 9 8 0", F(F_BLACK, 18), RED),
                text_img("VIDEO MEASURING", F(F_BLACK, 58), (255, 255, 255)),
                text_img("MACHINES", F(F_BLACK, 58), GREEN),
                text_img("Non-contact optical metrology for the shop floor", F(F_SEMI, 21), (215, 220, 224)))
    grad, kick, l1, l2, sub = HERO
    base.alpha_composite(grad)
    for spr, y, f0 in [(kick, 470, 2), (l1, 500, 5), (l2, 562, 9), (sub, 632, 14)]:
        a = ease_out((t - f0) / 8)
        paste(base, spr, 66 - 30 * (1 - a), y, a)


def draw_opener(base, t):
    if t < 84:
        a_out = 1 - ease_out((t - 74) / 10) if t > 74 else 1
        base.alpha_composite(new(color=(0, 0, 0, int(110 * a_out))))
        lh, y0 = 122, LH // 2 - 122
        for k, (spr, f0) in enumerate(HOOK_SPR):
            lt = (t - f0) / 7.0
            if lt < 0:
                continue
            s = 1.45 - 0.45 * back_out(lt)
            paste(base, spr, LW / 2, y0 + k * lh, ease_out(lt * 1.6) * a_out, s, "mm")
    if t >= 86:
        hero_title(base, t - 86)


# ================================================================ HUD + callouts
F_T, F_S, F_M = F(F_BLACK, 34), F(F_SEMI, 22), F(F_MONO, 15)
CALL = {
    "zfocus": ((640, 330), (70, 500), "CNC Z-AXIS + AUTO FOCUS", ("", "semi-automatic & fully automatic models")),
    "stage": ((560, 210), (70, 500), "PRECISION XY STAGE", ("", "on a solid granite base")),
    "knob": ((790, 460), (70, 500), "FINE MICROMETER CONTROL", ("", "manual X / Y drive")),
    "screw": ((1000, 240), (70, 500), "PRECISION DRIVE MECHANICS", ("SERVO CNC", "  X / Y / Z on fully automatic")),
    "scale": ((660, 490), (720, 110), "LINEAR SCALE", ("0.5 µm", "  resolution  ·  0.1 µm optional")),
    "led": ((630, 410), (770, 520), "LED CONTOUR BACKLIGHT", ("8-ZONE", "  programmable ring light")),
    "bolt": ((440, 370), (650, 520), "18–195X MAGNIFICATION", ("", "industrial colour CCD camera")),
}


def hud(base, t, n):
    a = ease_out(t / 6) * (1 - ease_out((t - n + 5) / 5) if t > n - 5 else 1)
    if a <= 0:
        return
    o = new(); d = SD(o)
    m, L, c = 26, 34, (255, 255, 255, int(150 * a))
    for (x, y, sx, sy) in [(m, m, 1, 1), (LW - m, m, -1, 1), (m, LH - m, 1, -1), (LW - m, LH - m, -1, -1)]:
        d.line((x, y, x + sx * L, y), fill=c, width=2)
        d.line((x, y, x, y + sy * L), fill=c, width=2)
    d.text((LW - 230, m + 8), "CRYSTAL VMM  ·  LIVE", F_M, (255, 255, 255, int(120 * a)))
    if (t // 10) % 2 == 0:
        d.ellipse((LW - 250, m + 11, LW - 240, m + 21), fill=(225, 30, 36, int(200 * a)))
    z = 41.0062 - t * 0.0011
    d.text((m + 8, LH - m - 26), f"X 12.5148   Y -3.2207   Z {z:7.4f}", F_M, (255, 255, 255, int(110 * a)))
    base.alpha_composite(o)


def callout(base, key, t, n):
    (tx, ty), (lx, ly), title, (val, rest) = CALL[key]
    out = 1 - ease_out((t - n + 6) / 5) if t > n - 6 else 1.0
    o = new(); d = SD(o)
    ta = ease_out(t / 6) * out
    if ta > 0:
        r = 22 - 8 * back_out(t / 7)
        c = (255, 255, 255, int(235 * ta))
        d.ellipse((tx - r, ty - r, tx + r, ty + r), outline=c, width=2)
        d.ellipse((tx - 3, ty - 3, tx + 3, ty + 3), fill=GREEN + (int(255 * ta),))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            d.line((tx + dx * (r + 4), ty + dy * (r + 4), tx + dx * (r + 12), ty + dy * (r + 12)), fill=c, width=2)
    tw = max(Lw(F_T, title), Lw(F_S, val + rest)) + 44
    ph = 86
    ax = lx if tx < lx else lx + tw
    ay = ly + 30
    ex = ax + (-40 if tx < lx else 40)
    pts = [(tx, ty), (ex, ay), (ax, ay)]
    lp = ease_out((t - 3) / 8)
    if lp > 0 and out > 0:
        segs = [(pts[0], pts[1]), (pts[1], pts[2])]
        lens = [math.hypot(b[0] - a_[0], b[1] - a_[1]) for a_, b in segs]
        rem = lp * sum(lens)
        for (a_, b), L in zip(segs, lens):
            if rem <= 0:
                break
            f = min(1, rem / L)
            d.line((a_[0], a_[1], a_[0] + (b[0] - a_[0]) * f, a_[1] + (b[1] - a_[1]) * f),
                   fill=(255, 255, 255, int(220 * out)), width=2)
            rem -= L
    pa = ease_out((t - 8) / 7) * out
    if pa > 0:
        sl = (1 - ease_out((t - 8) / 9)) * (-24 if tx > lx else 24)
        x0 = lx + sl
        d.rounded_rectangle((x0, ly, x0 + tw, ly + ph), 8, fill=(8, 10, 12, int(185 * pa)))
        d.rectangle((x0, ly + 10, x0 + 4, ly + ph - 10), fill=RED + (int(255 * pa),))
        d.text((x0 + 22, ly + 10), title, F_T, (255, 255, 255, int(255 * pa)))
        x = x0 + 22
        if val:
            d.text((x, ly + 52), val, F_S, GREEN + (int(255 * pa),)); x += Lw(F_S, val)
        d.text((x, ly + 52), rest, F_S, GREY + (int(255 * pa),))
    base.alpha_composite(o)


# ================================================================ software screens
LIME, DARK, PANEL, PANEL2, LINE = (92, 238, 52), (14, 16, 18), (28, 31, 35), (38, 42, 47), (70, 76, 84)
CYAN, OKG = (40, 210, 255), (60, 255, 120)
VX0, VY0, VX1, VY1 = 40, 70, 860, 560
VW, VH = VX1 - VX0, VY1 - VY0


def ui_frame(title, dro):
    im = new("RGB", None, DARK); d = SD(im)
    d.rectangle((0, 0, LW, 50), fill=PANEL)
    for k in range(9):
        d.rounded_rectangle((20 + k * 34, 14, 44 + k * 34, 36), 4, fill=PANEL2)
    d.text((360, 13), title, F(F_SEMI, 18), (150, 158, 166))
    d.ellipse((LW - 40, 17, LW - 24, 33), fill=RED)
    d.rectangle((VX0 - 2, VY0 - 2, VX1 + 1, VY1 + 1), outline=LINE, width=2)
    d.rectangle((890, 70, LW - 30, VY1), fill=PANEL)
    d.text((910, 84), "DRO", F(F_BLACK, 20), WHITE)
    fm = F(F_MONO, 30)
    for k, (ax, val) in enumerate(zip("XYZ", dro)):
        y = 124 + k * 58
        d.rounded_rectangle((910, y, LW - 50, y + 46), 6, fill=(10, 12, 14))
        d.text((924, y + 7), ax, F(F_BLACK, 24), CYAN)
        txt = f"{val:+9.4f}"
        d.text((LW - 62 - Lw(fm, txt), y + 6), txt, fm, (255, 214, 60))
    d.rectangle((40, 580, LW - 30, 690), fill=PANEL)
    return im, d


def dro_at(t, base, drift):
    return [b + dr * math.sin(t / 9 + k) * 0.5 + dr * t / 60 for k, (b, dr) in enumerate(zip(base, drift))]


def result_rows(d, rows, t0, t, x=910, y=310):
    fl, fv = F(F_SEMI, 17), F(F_MONO, 22)
    d.text((x, y - 4), "RESULTS", F(F_BLACK, 18), WHITE)
    for k, (lbl, val, ok) in enumerate(rows):
        a = ease_out((t - t0 - k * 6) / 6)
        if a <= 0:
            continue
        yy = y + 30 + k * 44
        col = tuple(int(c * a + 28 * (1 - a)) for c in WHITE)
        d.text((x, yy), lbl, fl, (150, 158, 166))
        d.text((x + 120, yy - 3), val, fv, col)
        if ok:
            d.rounded_rectangle((LW - 92, yy - 2, LW - 50, yy + 22), 5, fill=(20, 90, 40))
            d.text((LW - 84, yy - 1), "OK", F(F_BLACK, 16), OKG)


def label(d, x, y, txt):
    f = F(F_MONO, 18)
    w = Lw(f, txt)
    d.rectangle((x - 6, y - 3, x + w + 6, y + 23), fill=(255, 255, 255))
    d.text((x, y), txt, f, (10, 10, 10))


def bottom_strip(d, t, status):
    d.text((60, 596), status, F(F_SEMI, 18), (150, 158, 166))
    d.text((60, 630), "MAG 120X   ·   CONTOUR LIGHT 68%   ·   RING LIGHT 8-ZONE", F(F_SEMI, 16), (110, 118, 126))
    d.ellipse((LW - 80, 610, LW - 64, 626), fill=OKG if (t // 8) % 2 == 0 else (30, 80, 40))


def viewport():
    vp = new("RGB", (P(VW), P(VH)), LIME)
    return vp, SD(vp)


def screen_thread(t, n):
    im, d = ui_frame("Profile measurement  ·  Thread M10 × 1.5", dro_at(t, (12.4815, -3.2207, 41.0062), (0.02, 0, 0)))
    vp, vd = viewport()
    pitch = 118
    off = -t * 0.8
    depth = (pitch / 2) / math.tan(math.radians(30))
    top_root, bot_root = 160, 330
    top_crest, bot_crest = top_root - depth, bot_root + depth
    pts_top, pts_bot = [], []
    x = off - pitch
    while x < VW + pitch:
        pts_top += [(x, top_root), (x + pitch * 0.5, top_crest)]
        pts_bot += [(x, bot_root), (x + pitch * 0.5, bot_crest)]
        x += pitch
    vd.polygon(pts_top + list(reversed(pts_bot)), fill=(22, 22, 22))
    vd.line((0, VH / 2, VW, VH / 2), fill=RED, width=1)
    vd.line((VW / 2, 0, VW / 2, VH), fill=RED, width=1)
    sx = ease_out(t / (n * 0.45)) * VW
    if sx < VW:
        vd.line((sx, 0, sx, VH), fill=CYAN, width=2)
    for k in range(len(pts_top) - 1):
        (x0, y0), (x1, y1) = pts_top[k], pts_top[k + 1]
        for s in np.linspace(0, 1, 6):
            px, py = x0 + (x1 - x0) * s, y0 + (y1 - y0) * s
            if 0 < px < min(sx, VW):
                vd.ellipse((px - 2.5, py - 2.5, px + 2.5, py + 2.5), fill=CYAN)
    im.paste(vp, (P(VX0), P(VY0)))
    a = (t - n * 0.45) / 8
    if a > 0:
        cx = [p[0] for p in pts_top[1::2] if 200 < p[0] < VW - 150][:2]
        if len(cx) == 2:
            y = VY0 + top_crest - 28
            d.line((VX0 + cx[0], y, VX0 + cx[1], y), fill=WHITE, width=2)
            for c in cx:
                d.line((VX0 + c, y - 8, VX0 + c, y + 30), fill=WHITE, width=1)
            label(d, VX0 + (cx[0] + cx[1]) / 2 - 60, y - 34, "P 1.5003 mm")
        if a > 0.6:
            rx = [p[0] for p in pts_top[0::2] if 420 < p[0] < VW - 150][0]
            cxp, cyp, r = VX0 + rx, VY0 + top_root, 64
            d.arc((cxp - r, cyp - r, cxp + r, cyp + r), 240, 300, fill=WHITE, width=3)
            for ang in (240, 300):
                d.line((cxp, cyp, cxp + (r + 18) * math.cos(math.radians(ang)), cyp + (r + 18) * math.sin(math.radians(ang))),
                       fill=WHITE, width=1)
            label(d, cxp - 62, cyp - r - 52, "FLANK 60.02°")
    result_rows(d, [("Pitch", "1.5003", True), ("Flank", "60.02°", True), ("Major Ø", "9.976", True)], int(n * 0.5), t)
    bottom_strip(d, t, "Edge points: %d" % min(240, int(t * 5)))
    return im


HOLES = [(150, 150, 34), (300, 150, 40), (450, 150, 46), (600, 150, 52),
         (150, 330, 34), (300, 330, 40), (450, 330, 46), (600, 330, 52)]
DIAS = ["Ø 6.012", "Ø 7.008", "Ø 8.004", "Ø 9.011", "Ø 6.009", "Ø 7.013", "Ø 8.006", "Ø 9.002"]


def screen_holes(t, n):
    im, d = ui_frame("Feature measurement  ·  Hole plate", dro_at(t, (-10.5140, 2.0610, 38.4417), (0, 0.01, 0)))
    vp, vd = viewport()
    for (x, y, r) in HOLES:
        vd.ellipse((x - r, y - r, x + r, y + r), fill=(22, 22, 22))
    im.paste(vp, (P(VX0), P(VY0)))
    step = max(3, int(n * 0.65 / len(HOLES)))
    for k, ((x, y, r), dia) in enumerate(zip(HOLES, DIAS)):
        lt = (t - 4 - k * step) / 6
        if lt <= 0:
            continue
        a = ease_out(lt)
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
    bottom_strip(d, t, f"Circles detected: {done}")
    return im


def screen_report(t, n):
    im = Image.blend(screen_holes(n - 1, n), new("RGB", None, (0, 0, 0)), 0.45)
    s = ease_out(t / 9)
    sheet = new("RGB", (P(760), P(560)), (250, 251, 252)); sd = SD(sheet)
    sd.rectangle((0, 0, 760, 56), fill=(30, 34, 38))
    sd.text((24, 12), "INSPECTION REPORT", F(F_BLACK, 26), WHITE)
    sd.text((470, 18), "Part: HOLE PLATE-12", F(F_SEMI, 17), (200, 205, 210))
    xs = [24, 70, 250, 380, 520, 640]
    fh, fr = F(F_SEMI, 17), F(F_MONO, 19)
    for x, h in zip(xs, ["#", "Feature", "Nominal", "Measured", "Dev.", "Result"]):
        sd.text((x, 76), h, fh, (90, 96, 104))
    sd.line((20, 104, 740, 104), fill=(200, 204, 208), width=2)
    noms = ["6.000", "7.000", "8.000", "9.000", "6.000", "7.000", "8.000", "9.000"]
    for k in range(8):
        a = ease_out((t - 6 - k * 2) / 4)
        if a <= 0:
            continue
        y = 116 + k * 50
        meas = DIAS[k].split()[1]
        c = tuple(int(30 + (1 - a) * 200) for _ in range(3))
        for x, v in zip(xs, [str(k + 1), "Circle Ø", noms[k], meas, f"{float(meas) - float(noms[k]):+.3f}"]):
            sd.text((x, y), v, fr, c)
        sd.rounded_rectangle((640, y - 2, 700, y + 26), 6, fill=(28, 150, 70))
        sd.text((656, y + 1), "OK", F(F_BLACK, 17), (255, 255, 255))
        sd.line((20, y + 38, 740, y + 38), fill=(232, 234, 236), width=1)
    k = 0.9 + 0.1 * s
    sh = sheet.resize((int(sheet.width * k), int(sheet.height * k)), Image.LANCZOS)
    x = (PW - sh.width) // 2
    y = int(PH + P(40) - (PH + P(40) - (PH - sh.height) // 2) * s)
    shadow = Image.new("RGBA", (sh.width + P(60), sh.height + P(60)), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle((P(30), P(30), sh.width + P(30), sh.height + P(30)), fill=(0, 0, 0, 150))
    im = im.convert("RGBA")
    im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18 * S)), (x - P(30), y - P(18)))
    im = im.convert("RGB")
    im.paste(sh, (x, y))
    return im


TAGS = {"thread": "AUTO EDGE DETECTION", "holes": "ONE-CLICK CIRCLE FITTING", "report": "INSTANT INSPECTION REPORT"}


def tag(base, key, t):
    a = ease_out((t - 4) / 7)
    if a <= 0:
        return
    f = F(F_BLACK, 20)
    w = Lw(f, TAGS[key]) + 48
    o = new(); d = SD(o)
    x, y = LW - 60 - w, 606
    d.rounded_rectangle((x, y, x + w, y + 44), 22, fill=(60, 255, 120, int(235 * a)))
    d.text((x + 24, y + 9), TAGS[key], f, (8, 20, 12, int(255 * a)))
    base.alpha_composite(o)


def screen_push(img, t, n):
    z = 1.0 + 0.035 * (t / n)
    cw, ch = PW / z, PH / z
    x0, y0 = (PW - cw) / 2, (PH - ch) / 2
    return img.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((PW, PH), Image.LANCZOS)


# ================================================================ lineup
SERIES = [
    ("ref_manual.png", "MANUAL", ["AA-9011M", "AA-9012M", "AA-9013M"]),
    ("ref_semiauto.png", "SEMI-AUTOMATIC", ["AA-9021SA", "AA-9022SA", "AA-9023SA"]),
    ("ref_fullauto.png", "FULLY AUTOMATIC", ["AA-9031A", "AA-9032A", "AA-9033A"]),
    ("ref_cabinet.png", "WITH CABINET", ["AA-9041AC", "AA-9042AC", "AA-9043AC", "AA-9044AC"]),
    ("ref_vms.png", "VMS SERIES", ["AA-9051V", "AA-9052V", "AA-9053V"]),
]
CW_, CH_, GAP = 224, 400, 18
LINEUP = None


def make_cards():
    cards = []
    fs, fm, fn = F(F_BLACK, 17), F(F_SEMI, 16), F(F_BLACK, 15)
    for k, (img, name, models) in enumerate(SERIES):
        body = new("RGBA", (P(CW_), P(CH_)), (255, 255, 255, 255)); d = SD(body)
        ph = Image.open(img).convert("RGB")
        a = np.asarray(ph).copy(); a[a.min(axis=2) > 232] = 255; ph = Image.fromarray(a)
        ph.thumbnail((P(CW_ - 28), P(236)), Image.LANCZOS)
        body.paste(ph, ((body.width - ph.width) // 2, P(14) + (P(236) - ph.height) // 2))
        d.rectangle((0, 260, CW_, CH_), fill=(18, 21, 24))
        d.rectangle((0, 260, CW_, 264), fill=RED)
        d.text((16, 274), f"0{k + 1}", fn, RED)
        d.text((44, 272), name, fs, (255, 255, 255))
        for j, mo in enumerate(models):
            d.text((16, 306 + j * 21), mo, fm, (205, 212, 218))
        m = Image.new("L", body.size, 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, body.width - 1, body.height - 1), P(16), fill=255)
        c = new("RGBA", body.size); c.paste(body, (0, 0), m)
        cards.append(c)
    return cards


def draw_lineup(t):
    global LINEUP
    if LINEUP is None:
        X, Y, _, _ = grid_xy()
        bg = np.zeros((PH, PW, 3), np.float32); bg[:] = (10, 12, 14)
        dd = np.sqrt(((X - LW / 2) / 760) ** 2 + ((Y - LH * 0.55) / 420) ** 2)
        bg += (np.clip(1 - dd, 0, 1) ** 2)[..., None] * np.array([10, 34, 18])
        sh = Image.new("RGBA", (P(CW_ + 40), P(CH_ + 40)), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((P(20), P(26), P(CW_ + 20), P(CH_ + 26)), P(16), fill=(0, 0, 0, 160))
        LINEUP = (Image.fromarray(bg.astype(np.uint8)).convert("RGBA"), make_cards(),
                  text_img("AVAILABLE MODELS", F(F_BLACK, 44), (255, 255, 255)),
                  text_img("5 series  ·  16 models  ·  available now", F(F_SEMI, 22), GREEN),
                  sh.filter(ImageFilter.GaussianBlur(12 * S)))
    bg, cards, h1, h2, shadow = LINEUP
    fr = bg.copy()
    paste(fr, h1, LW / 2, 70, ease_out(t / 8), 1.0, "mm")
    paste(fr, h2, LW / 2, 118, ease_out((t - 5) / 8), 1.0, "mm")
    x0, y0 = (LW - (5 * CW_ + 4 * GAP)) / 2, 170
    for k, c in enumerate(cards):
        lt = (t - 8 - k * 5) / 10
        if lt <= 0:
            continue
        dy = (1 - ease_out(lt)) * 80
        paste(fr, shadow, x0 + k * (CW_ + GAP) - 20, y0 + dy - 20, ease_out(lt))
        paste(fr, c, x0 + k * (CW_ + GAP), y0 + dy, ease_out(lt * 1.4))
    return fr


# ================================================================ end card with logo animation
CONTACT = ["Armatech Associates", "W-174, A 'S' Block, M.I.D.C, Bhosari,", "Pune 411026",
           "GST No. 27AACFA6934B1ZT", "Cell: 7020991684", "Email: armatech@gmail.com"]
LOGO_INTRO, LOGO_MOVE = 62, 20
LOGO_BIG_W, LOGO_FINAL_W, LOGO_FINAL_TOP = 600, 300, 86
END = None
_PLATES = {}


def make_button():
    fb = F(F_BLACK, 26)
    txt = "BOOK A LIVE DEMO"
    bw, bh = Lw(fb, txt) + 80, 66
    size = (P(bw + 60), P(bh + 60))
    glow = new("RGBA", size); SD(glow).rounded_rectangle((30, 30, 30 + bw, 30 + bh), bh / 2, fill=RED + (200,))
    glow = glow.filter(ImageFilter.GaussianBlur(16 * S))
    btn = new("RGBA", size); bd = ImageDraw.Draw(btn)
    bd.rounded_rectangle((P(30), P(30), P(30 + bw), P(30 + bh)), P(bh / 2), fill=RED)
    l, t, r, b = fb.getbbox(txt)
    bd.text((P(30) + (P(bw) - (r - l)) / 2 - l, P(30) + (P(bh) - (b - t)) / 2 - t), txt, font=fb, fill=(255, 255, 255))
    return glow, btn


def make_end():
    X, Y, xx, yy = grid_xy()
    bg = np.zeros((PH, PW, 3), np.float32); bg[:] = (6, 8, 10)
    dd = np.sqrt(((X - LW * 0.3) / 640) ** 2 + ((Y - LH / 2) / 420) ** 2)
    bg += (np.clip(1 - dd, 0, 1) ** 2)[..., None] * np.array([8, 40, 20])
    gstep = P(40)
    bg += ((((xx % gstep) < 1) | ((yy % gstep) < 1)).astype(np.float32) * 6)[..., None] * np.array([0.4, 1, 0.6])
    bgi = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).convert("RGBA")

    cx = 360
    final_body_h = (plate_at(70, LOGO_FINAL_W).height - 2 * LA_M) / S
    left = new(); dl = SD(left)
    ft = F(F_BLACK, 46)
    parts = [("5 SERIES ", (255, 255, 255)), ("·", GREEN), (" 16 MODELS", (255, 255, 255))]
    tw = sum(Lw(ft, p) for p, _ in parts); x = cx - tw / 2; ty = LOGO_FINAL_TOP + final_body_h + 30
    for p, c in parts:
        dl.text((x, ty), p, ft, c); x += Lw(ft, p)
    fs = F(F_SEMI, 20)
    for j, s_ in enumerate(["Video Measuring Machines", "accuracy from 2 µm  ·  up to 195X"]):
        dl.text((cx - Lw(fs, s_) / 2, ty + 66 + j * 28), s_, fs, (200, 206, 210))
    btn_y = ty + 140

    right = new(); dr = SD(right)
    px0, py0, pw, phh = 700, 170, 520, 360
    dr.rounded_rectangle((px0, py0, px0 + pw, py0 + phh), 18, fill=(255, 255, 255, 18), outline=(255, 255, 255, 60), width=1)
    dr.rectangle((px0, py0 + 24, px0 + 5, py0 + 84), fill=RED)
    dr.text((px0 + 30, py0 + 26), "CONTACT", F(F_BLACK, 18), RED)
    dr.text((px0 + 30, py0 + 52), CONTACT[0], F(F_BLACK, 32), (255, 255, 255))
    fl = F(F_SEMI, 21)
    y = py0 + 112
    for line in CONTACT[1:3]:
        dr.text((px0 + 30, y), line, fl, (214, 220, 224)); y += 30
    y += 14
    dr.line((px0 + 30, y, px0 + pw - 30, y), fill=(255, 255, 255, 50), width=1); y += 20
    for line in CONTACT[4:]:
        k, v = line.split(": ", 1)
        dr.text((px0 + 30, y), k.upper(), F(F_BLACK, 15), GREEN)
        dr.text((px0 + 110, y - 6), v, F(F_BLACK, 24), (255, 255, 255)); y += 46
    dr.text((px0 + 30, y + 4), CONTACT[3], F(F_SEMI, 17), (150, 158, 166))
    return (bgi, left, right, btn_y) + make_button()


LA_M = 40      # logo_anim plate shadow margin (physical px, fixed in logo_anim)


def plate_at(t_anim, w_logical):
    key = (min(int(t_anim), 70), P(w_logical))
    if key in _PLATES:
        return _PLATES[key]
    p = LA.logo_plate(key[0], key[1])
    if key[0] >= 70:
        _PLATES[key] = p
    return p


def draw_end(t):
    global END
    if END is None:
        END = make_end()
    bgi, left, right, btn_y, bglow, btn = END
    fr = bgi.copy()
    m = ease_out((t - LOGO_INTRO) / LOGO_MOVE) if t > LOGO_INTRO else 0.0
    m = m * m * (3 - 2 * m)
    w = LOGO_BIG_W + (LOGO_FINAL_W - LOGO_BIG_W) * m
    pl = plate_at(t, w)
    body_h = (pl.height - 2 * LA_M) / S
    cx = LW / 2 + (360 - LW / 2) * m
    top_big = (LH - body_h) / 2
    top = top_big + (LOGO_FINAL_TOP - top_big) * m
    fr.alpha_composite(pl, (int(round(cx * S - pl.width / 2)), int(round(top * S - LA_M))))
    t = t - (LOGO_INTRO + LOGO_MOVE)
    if t < 0:
        return fr
    sweep = ease_out(t / 26.0)
    sx = -40 + sweep * (LW + 80)
    if sx > 0:
        mk = Image.new("L", (PW, PH), 0); ImageDraw.Draw(mk).rectangle((0, 0, min(P(sx), PW), PH), fill=255)
        rev = new(); rev.paste(left, (0, 0), mk)
        paste(fr, rev, 0, 0, ease_out((t - 2) / 16))
    ra = ease_out((t - 18) / 12)
    paste(fr, right, 30 * (1 - ra), 0, ra)
    if t < 34:
        line = new(); ld = SD(line)
        for k in range(60):
            ld.line((sx - k, 0, sx - k, LH), fill=GREEN + (int(90 * (1 - k / 60) ** 2),), width=1)
        ld.rectangle((sx - 1, 0, sx + 2, LH), fill=(200, 255, 215, 255))
        paste(fr, line, 0, 0, 1 - ease_out((t - 26) / 8) if t > 26 else 1)
    bt = (t - 30) / 9.0
    if bt > 0:
        sc = 0.6 + 0.4 * back_out(bt)
        pulse = 0.55 + 0.45 * (0.5 + 0.5 * math.sin((t - 40) / 30 * 2 * math.pi)) if t > 40 else ease_out(bt)
        cy = btn_y + btn.height / S / 2
        paste(fr, bglow, 360, cy, pulse * ease_out(bt), sc, "mm")
        paste(fr, btn, 360, cy, ease_out(bt * 1.5), sc, "mm")
    return fr


# ================================================================ timeline
SEGS = [("opener", 5.0, "opener"), ("zfocus", 3.0, "video"), ("stage", 3.5, "video"), ("knob", 3.0, "video"),
        ("screw", 3.5, "video"), ("scale", 3.5, "video"), ("led", 3.0, "video"), ("bolt", 3.0, "video"),
        ("thread", 4.0, "screen"), ("holes", 3.5, "screen"), ("report", 2.5, "screen"),
        ("lineup", 4.5, "lineup"), ("end", 7.5, "end")]
SCREENS = {"thread": screen_thread, "holes": screen_holes, "report": screen_report}
TL, _f = [], 0
for name, secs, kind in SEGS:
    n = int(round(secs * FPS)); TL.append((name, _f, n, kind)); _f += n
TOTAL = _f
CUTS = [s for _, s, _, _ in TL[1:]]
BIG = {TL[1][1], TL[8][1], TL[11][1], TL[12][1]}


def flash(img, f):
    for c in CUTS:
        k = f - c
        big = c in BIG
        if (-3 <= k <= 2) if big else (0 <= k <= 1):
            s = (1 - abs(k + 0.5) / 3.5) if big else (0.35 if k == 0 else 0.1)
            a = np.asarray(img.convert("RGB")).astype(np.float32)
            if big:
                shift = P(50 * s) * (1 if k < 0 else -1)
                a = sum(np.roll(a, int(shift * i / 5), axis=1) for i in range(6)) / 6
            a = a + (255 - a) * (0.8 * s ** 1.5 if big else s)
            return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")
    return img


def compose(f):
    for name, s, n, kind in TL:
        if s <= f < s + n:
            t = f - s; break
    if kind == "opener":
        base = Image.fromarray(vframe(name, t)).convert("RGBA"); draw_opener(base, t)
    elif kind == "video":
        base = Image.fromarray(vframe(name, t)).convert("RGBA"); hud(base, t, n); callout(base, name, t, n)
    elif kind == "screen":
        base = screen_push(SCREENS[name](t, n), t, n).convert("RGBA"); tag(base, name, t)
    elif kind == "lineup":
        base = draw_lineup(t)
    else:
        base = draw_end(t)
    return flash(base, f)


def main():
    if sys.argv[1] == "preview":
        os.makedirs("v5hd/preview", exist_ok=True)
        for f in map(int, sys.argv[2:]):
            compose(f).convert("RGB").save(f"v5hd/preview/hd_{f:04d}.png")
            print("preview", f, f"{f / FPS:.2f}s", flush=True)
        return
    out = sys.argv[2] if len(sys.argv) > 2 else f"VMM_promo_v5_{PH}p.mp4"
    dur = TOTAL / FPS
    cmd = [FF, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{PW}x{PH}", "-r", str(FPS), "-i", "-",
           "-i", "audio/music_v5_mix.wav", "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k",
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
           "-t", f"{dur:.3f}", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(TOTAL):
        p.stdin.write(compose(f).convert("RGB").tobytes())
        if f % 150 == 0:
            print("frame", f, flush=True)
    p.stdin.close(); p.wait()
    print("done", out, p.returncode, f"{dur:.2f}s", f"{PW}x{PH}")


if __name__ == "__main__":
    main()
