"""Step 4 edit: composite the 25s promo (1280x720 @30fps) with Pillow + ffmpeg.

Usage:
  python edit.py preview 60 240 450 690   -> preview/frame_XXXX.png
  python edit.py render                   -> VMM_promo_720p.mp4
"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FF = r"C:\Users\lunaw\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
W, H, FPS = 1280, 720, 30
TOTAL = 25 * FPS                     # 750
HOOK = 3 * FPS                       # 0-89
SEG = 108                            # 3.6s per series clip
SEG0 = HOOK                          # 90
END0 = SEG0 + 5 * SEG                # 630
CUTS = [SEG0 + k * SEG for k in range(6)]   # 90,198,306,414,522,630

GREEN = (60, 255, 120)
RED = (225, 30, 36)
GREY = (170, 176, 182)
F_BLACK = r"C:\Windows\Fonts\seguibl.ttf"
F_BOLD = r"C:\Windows\Fonts\segoeuib.ttf"
F_SEMI = r"C:\Windows\Fonts\seguisb.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


# ---------------------------------------------------------------- source frames
# norm/clip_N.mp4 are 1280x720 30fps; clip_2r is clip 2 reversed (used as a pull-out in segment 2)
SEG_SRC = ["norm/clip_1.mp4", "norm/clip_2r.mp4", "norm/clip_3.mp4", "norm/clip_4.mp4", "norm/clip_5.mp4"]
SEG_ZOOM = [1.0, 1.12, 1.0, 1.0, 1.0]
SRC_OFFSET = 6   # skip the first frames of each clip (start-frame settle)


class Reader:
    def __init__(self, path):
        self.path, self.proc, self.pos = path, None, 0

    def _open(self, start):
        if self.proc:
            self.proc.kill()
        self.proc = subprocess.Popen(
            [FF, "-v", "error", "-ss", f"{start / FPS:.4f}", "-i", self.path,
             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.pos = start

    def frame(self, idx):
        if self.proc is None or idx < self.pos:
            self._open(idx)
        last = None
        while self.pos <= idx:
            buf = self.proc.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:            # past end: hold last frame
                return last if last is not None else np.zeros((H, W, 3), np.uint8)
            last = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
            self.pos += 1
        self._last = last
        return last


READERS = {}


def src(path, idx):
    r = READERS.setdefault(path, Reader(path))
    if r.proc is not None and idx == r.pos - 1:
        return r._last
    return r.frame(idx)


def zoom(img, z):
    if z == 1.0:
        return img
    cw, ch = int(W / z), int(H / z)
    x0, y0 = (W - cw) // 2, (H - ch) // 2
    return img.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.LANCZOS)


# ---------------------------------------------------------------- helpers
def ease_out(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def back_out(t, s=1.9):
    t = min(max(t, 0.0), 1.0) - 1
    return t * t * ((s + 1) * t + s) + 1


def text_img(txt, fnt, fill, glow=None):
    """Tight RGBA text sprite, optional soft glow."""
    l, t, r, b = fnt.getbbox(txt)
    pad = 30 if glow else 4
    im = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - l, pad - t), txt, font=fnt, fill=fill)
    if glow:
        g = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).text((pad - l, pad - t), txt, font=fnt, fill=glow)
        g = g.filter(ImageFilter.GaussianBlur(14))
        im = Image.alpha_composite(Image.alpha_composite(g, g), im)
    return im, pad


def paste(base, sprite, x, y, alpha=1.0, scale=1.0, anchor="lt"):
    """Composite sprite onto base (RGBA) at x,y with alpha/scale. anchor lt or mm."""
    if alpha <= 0.003:
        return
    sp = sprite
    if abs(scale - 1.0) > 1e-3:
        sp = sp.resize((max(1, int(sp.width * scale)), max(1, int(sp.height * scale))), Image.LANCZOS)
    if alpha < 1.0:
        a = sp.getchannel("A").point(lambda v: int(v * alpha))
        sp = sp.copy(); sp.putalpha(a)
    if anchor == "mm":
        x, y = x - sp.width // 2, y - sp.height // 2
    base.alpha_composite(sp, (int(x), int(y)))


# ---------------------------------------------------------------- HOOK sprites
F_HOOK = font(F_BLACK, 118)
HOOK_WORDS = [("MEASURE", (255, 255, 255), None, 6),
              ("TO THE", (255, 255, 255), None, 22),
              ("MICRON.", GREEN, (60, 255, 120, 200), 38)]
HOOK_SPR = [(text_img(w, F_HOOK, c, g), f) for w, c, g, f in HOOK_WORDS]
VIGNETTE = None


def vignette():
    global VIGNETTE
    if VIGNETTE is None:
        yy, xx = np.mgrid[0:H, 0:W]
        d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        a = np.clip((d - 0.45) / 0.9, 0, 1) * 200
        v = np.zeros((H, W, 4), np.uint8); v[..., 3] = a.astype(np.uint8)
        VIGNETTE = Image.fromarray(v, "RGBA")
    return VIGNETTE


def draw_hook(base, t):
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 95))
    base.alpha_composite(dark)
    base.alpha_composite(vignette())
    line_h = 122
    y0 = H // 2 - line_h
    for k, ((spr, pad), f0) in enumerate(HOOK_SPR):
        lt = (t - f0) / 7.0
        if lt < 0:
            continue
        s = 1.45 - 0.45 * back_out(lt)
        a = ease_out(lt * 1.6)
        paste(base, spr, W // 2, y0 + k * line_h, a, s, "mm")


# ---------------------------------------------------------------- LOWER THIRDS
SERIES = [
    ("01", "MANUAL VMM", "AA-9011M · 9012M · 9013M",
     [("200→400", "mm", "X-AXIS RANGE"), ("2.5", "µm", "REPEATABILITY"), ("195", "X", "MAX MAGNIFICATION")]),
    ("02", "SEMI-AUTOMATIC", "AA-9021SA · 9022SA · 9023SA",
     [("CNC", "Z-AXIS", "+ AUTO FOCUS"), ("±2.5", "µm", "BEST REPEATABILITY"), ("0.5", "µm", "LINEAR SCALE")]),
    ("03", "FULLY AUTOMATIC", "AA-9031A · 9032A · 9033A",
     [("SERVO", "CNC", "X / Y / Z AXES"), ("160", "X", "AUTO ZOOM LENS"), ("1.3", "MP", "COLOUR CCD")]),
    ("04", "WITH CABINET", "AA-9041AC → 9044AC",
     [("600×500", "mm", "MAX XY RANGE"), ("2", "µm", "BEST REPEATABILITY"), ("1–10", "X", "AUTO ZOOM")]),
    ("05", "VMS SERIES", "AA-9051V · 9052V · 9053V",
     [("0.001", "mm", "LINEAR SCALE"), ("108", "mm", "WORKING DISTANCE"), ("188", "X", "MAX MAGNIFICATION")]),
]
F_NUM = font(F_BLACK, 26)
F_NAME = font(F_BLACK, 56)
F_MODEL = font(F_SEMI, 21)
F_STAT = font(F_BLACK, 44)
F_UNIT = font(F_BOLD, 20)
F_LBL = font(F_SEMI, 14)


def has_glyphs(fnt, s):
    return all(fnt.getmask(ch).getbbox() is not None or ch.isspace() for ch in s)


def stat_sprite(num, unit, lbl):
    fnum = F_STAT if has_glyphs(F_STAT, num) else font(F_BOLD, 44)
    nl, nt, nr, nb = fnum.getbbox(num)
    ul, ut, ur, ub = F_UNIT.getbbox(unit)
    ll, lt, lr, lb = F_LBL.getbbox(lbl, )
    w = max(nr - nl + 6 + ur - ul, lr - ll) + 8
    h = 52 + 26
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((-nl, 2 - nt), num, font=fnum, fill=(255, 255, 255))
    base_y = 2 + (nb - nt)                 # baseline-ish bottom of number
    d.text((nr - nl + 6 - ul, base_y - (ub - ut) - ut - 2), unit, font=F_UNIT, fill=GREEN)
    d.text((-ll, 58 - lt), lbl, font=F_LBL, fill=GREY)
    return im


GRAD = None


def bottom_gradient():
    global GRAD
    if GRAD is None:
        g = np.zeros((H, W, 4), np.uint8)
        ys = np.arange(H)
        a = np.clip((ys - 380) / (H - 380), 0, 1) ** 1.3 * 235
        g[..., 3] = a[:, None].astype(np.uint8)
        GRAD = Image.fromarray(g, "RGBA")
    return GRAD


LT = []
for num, name, models, stats in SERIES:
    LT.append(dict(
        num=text_img(num, F_NUM, RED)[0],
        name=text_img(name, F_NAME, (255, 255, 255))[0],
        models=text_img(models, F_MODEL, (215, 220, 224))[0],
        stats=[stat_sprite(*s) for s in stats]))


def draw_lower_third(base, k, t):
    L = LT[k]
    out = 1.0 - ease_out((t - (SEG - 7)) / 5.0) if t > SEG - 7 else 1.0
    g = bottom_gradient()
    ga = ease_out(t / 8.0) * out
    if ga < 1.0:
        a = g.getchannel("A").point(lambda v: int(v * ga)); g = g.copy(); g.putalpha(a)
    base.alpha_composite(g)
    x0, ytop = 64, 548
    # red accent bar grows downward
    bh = int(118 * ease_out((t - 3) / 9.0))
    if bh > 0 and out > 0:
        bar = Image.new("RGBA", (7, bh), RED + (int(255 * out),))
        base.alpha_composite(bar, (x0, ytop))
    slide = (1 - ease_out((t - 6) / 10.0)) * -40
    a1 = ease_out((t - 6) / 8.0) * out
    paste(base, L["num"], x0 + 24 + slide, ytop - 4, a1)
    paste(base, L["name"], x0 + 22 + slide, ytop + 22, a1)
    paste(base, L["models"], x0 + 24 + slide * 0.5, ytop + 92, ease_out((t - 12) / 8.0) * out)
    # stats: right-aligned row, staggered pops
    gap = 40
    widths = [s.width for s in L["stats"]]
    x = W - 64 - sum(widths) - gap * 2
    for j, s in enumerate(L["stats"]):
        st = (t - (18 + 6 * j)) / 8.0
        if st > 0:
            sc = 0.55 + 0.45 * back_out(st)
            cx, cy = x + s.width / 2, ytop + 40 + s.height / 2
            paste(base, s, cx, cy, ease_out(st * 1.5) * out, sc, "mm")
        x += widths[j] + gap


# ---------------------------------------------------------------- END CARD
def make_logo_plate():
    lg = Image.open("logo.png").convert("RGB")
    a = np.asarray(lg).copy()
    a[(a.min(axis=2) > 225)] = 255                 # clean off-white page bg
    lg = Image.fromarray(a)
    lg.thumbnail((300, 214), Image.LANCZOS)
    pw, ph = lg.width + 56, lg.height + 40
    plate = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    m = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, pw - 1, ph - 1), 22, fill=255)
    plate.paste(Image.new("RGBA", (pw, ph), (255, 255, 255, 255)), (0, 0), m)
    plate.paste(lg, (28, 20))
    return plate


def make_end_static():
    bg = np.zeros((H, W, 3), np.float32)
    bg[:] = (6, 8, 10)
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / 700) ** 2 + ((yy - H / 2) / 420) ** 2)
    glow = np.clip(1 - d, 0, 1) ** 2
    bg += glow[..., None] * np.array([8, 40, 20], np.float32)
    # faint measurement grid
    grid = ((xx % 40 == 0) | (yy % 40 == 0)).astype(np.float32) * 7
    bg += grid[..., None] * np.array([0.4, 1.0, 0.6])
    bgimg = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).convert("RGBA")

    content = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    plate = make_logo_plate()
    content.alpha_composite(plate, ((W - plate.width) // 2, 70))
    title_y = 70 + plate.height + 36
    ft = font(F_BLACK, 62)
    parts = [("5 SERIES ", (255, 255, 255)), ("·", GREEN), (" 16 MODELS", (255, 255, 255))]
    tw = sum(ft.getlength(p) for p, _ in parts)
    x = (W - tw) / 2
    d = ImageDraw.Draw(content)
    for p, c in parts:
        d.text((x, title_y), p, font=ft, fill=c); x += ft.getlength(p)
    fs = font(F_SEMI, 25)
    sub = "Video Measuring Machines  ·  accuracy from 2 µm  ·  up to 195X"
    d.text(((W - fs.getlength(sub)) / 2, title_y + 88), sub, font=fs, fill=(200, 206, 210))
    btn_y = title_y + 150
    return bgimg, content, btn_y


def make_button():
    fb = font(F_BLACK, 26)
    txt = "BOOK A LIVE DEMO"
    bw, bh = int(fb.getlength(txt)) + 80, 66
    im = Image.new("RGBA", (bw + 60, bh + 60), (0, 0, 0, 0))
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle((30, 30, 30 + bw, 30 + bh), bh // 2, fill=RED + (200,))
    glow = glow.filter(ImageFilter.GaussianBlur(16))
    btn = Image.new("RGBA", im.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(btn)
    bd.rounded_rectangle((30, 30, 30 + bw, 30 + bh), bh // 2, fill=RED)
    l, t, r, b = fb.getbbox(txt)
    bd.text((30 + (bw - (r - l)) / 2 - l, 30 + (bh - (b - t)) / 2 - t), txt, font=fb, fill=(255, 255, 255))
    return glow, btn


END = None


def draw_end(t):
    global END
    if END is None:
        END = make_end_static() + make_button()
    bgimg, content, btn_y, bglow, btn = END
    fr = bgimg.copy()
    sweep = ease_out(t / 26.0)                       # scan line pass 0..26 frames
    sx = int(-40 + sweep * (W + 80))
    # reveal content left of the scan line
    if sx > 0:
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).rectangle((0, 0, min(sx, W), H), fill=255)
        rev = Image.new("RGBA", (W, H), (0, 0, 0, 0)); rev.paste(content, (0, 0), m)
        # settle: slight fade-in of the revealed content
        a = ease_out((t - 2) / 18.0)
        paste(fr, rev, 0, 0, a)
    # scan line + trailing glow
    if t < 34:
        line = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(line)
        for k in range(60):
            alpha = int(90 * (1 - k / 60) ** 2)
            ld.line([(sx - k, 0), (sx - k, H)], fill=GREEN + (alpha,))
        ld.rectangle((sx - 1, 0, sx + 2, H), fill=(200, 255, 215, 255))
        fade = 1 - ease_out((t - 26) / 8.0) if t > 26 else 1
        paste(fr, line.filter(ImageFilter.GaussianBlur(1.2)), 0, 0, fade)
    # button pops in, then breathes
    bt = (t - 30) / 9.0
    if bt > 0:
        sc = 0.6 + 0.4 * back_out(bt)
        pulse = 0.55 + 0.45 * (0.5 + 0.5 * math.sin((t - 40) / 30 * 2 * math.pi)) if t > 40 else ease_out(bt)
        cx, cy = W // 2, btn_y + btn.height // 2
        paste(fr, bglow, cx, cy, pulse * ease_out(bt), sc, "mm")
        paste(fr, btn, cx, cy, ease_out(bt * 1.5), sc, "mm")
    return fr


# ---------------------------------------------------------------- transitions
def whip_flash(img, f):
    """6-frame flash/whip around each cut: frames c-3..c+2."""
    for c in CUTS:
        k = f - c
        if -3 <= k <= 2:
            strength = 1 - abs(k + 0.5) / 3.5            # peak at the cut
            a = np.asarray(img.convert("RGB")).astype(np.float32)
            shift = int(70 * strength) * (1 if k < 0 else -1)
            acc = np.zeros_like(a)
            n = 7
            for s in range(n):
                acc += np.roll(a, int(shift * s / (n - 1)), axis=1)
            a = acc / n
            a = a + (255 - a) * (0.85 * strength ** 1.5)
            return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")
    return img


# ---------------------------------------------------------------- frame composer
def compose(f):
    if f < HOOK:
        base = Image.fromarray(src("norm/clip_2.mp4", f)).convert("RGBA")
        draw_hook(base, f)
    elif f < END0:
        k = (f - SEG0) // SEG
        t = (f - SEG0) % SEG
        base = zoom(Image.fromarray(src(SEG_SRC[k], t + SRC_OFFSET)), SEG_ZOOM[k]).convert("RGBA")
        draw_lower_third(base, k, t)
    else:
        base = draw_end(f - END0)
    return whip_flash(base, f)


def main():
    mode = sys.argv[1]
    if mode == "preview":
        os.makedirs("preview", exist_ok=True)
        for f in map(int, sys.argv[2:]):
            compose(f).convert("RGB").save(f"preview/frame_{f:04d}.png")
            print("preview", f, f"{f / FPS:.2f}s")
        return
    out = sys.argv[2] if len(sys.argv) > 2 else "VMM_promo_720p.mp4"
    cmd = [FF, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-"]
    if os.path.exists("audio/music_25s.wav"):
        cmd += ["-i", "audio/music_25s.wav", "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", "-t", "25", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(TOTAL):
        p.stdin.write(compose(f).convert("RGB").tobytes())
        if f % 75 == 0:
            print("frame", f, flush=True)
    p.stdin.close(); p.wait()
    print("done", out, p.returncode)


if __name__ == "__main__":
    main()
