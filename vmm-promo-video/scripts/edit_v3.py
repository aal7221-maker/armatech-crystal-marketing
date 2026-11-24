"""v3 edit: 30s technical promo (1280x720 @30fps).

python edit_v3.py preview f1 f2 ...   -> v3/preview/v3_XXXX.png
python edit_v3.py render [out.mp4]    -> VMM_promo_v3_720p.mp4
"""
import os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
import edit as E          # hook, end card, text helpers from v1
import screens as S       # procedural software screens

FF, W, H, FPS = E.FF, 1280, 720, 30
TOTAL = 30 * FPS
GREEN, RED, GREY = E.GREEN, E.RED, (176, 184, 190)

# (name, start_frame, n_frames, kind, source)
TL = []
_f = 0
for name, secs, kind, src in [
    ("hook",   3.0, "video",  "v3/seg/zfocus.mp4"),
    ("hero",   2.5, "still",  "v2/stills/s_hero_v2.png"),
    ("stage",  2.0, "video",  "v3/seg/stage.mp4"),
    ("knob",   1.8, "video",  "v3/seg/knob.mp4"),
    ("screw",  2.5, "video",  "v3/seg/screw.mp4"),
    ("scale",  2.0, "video",  "v3/seg/scale.mp4"),
    ("led",    1.5, "video",  "v3/seg/led.mp4"),
    ("bolt",   1.5, "video",  "v3/seg/bolt.mp4"),
    ("thread", 3.0, "screen", S.screen_thread),
    ("holes",  2.7, "screen", S.screen_holes),
    ("report", 2.5, "screen", S.screen_report),
    ("end",    5.0, "end",    None)]:
    n = int(round(secs * FPS))
    TL.append((name, _f, n, kind, src)); _f += n
assert _f == TOTAL, _f
CUTS = [s for _, s, _, _, _ in TL[1:]]
BIG_CUTS = {TL[1][1], TL[8][1], TL[11][1]}          # hook->hero, into screens, end card

# callouts: target point, label anchor (top-left of plate), title, sub (value part green)
CALL = {
    "stage": ((560, 210), (70, 520), "PRECISION XY STAGE", ("", "on a solid granite base")),
    "knob":  ((790, 460), (70, 520), "FINE MICROMETER CONTROL", ("", "manual X / Y  ·  CNC Z on semi-auto")),
    "screw": ((1000, 240), (70, 520), "PRECISION DRIVE MECHANICS", ("SERVO CNC", " X / Y / Z on fully automatic")),
    "scale": ((660, 490), (760, 120), "LINEAR SCALE", ("0.5 µm", " resolution  ·  0.1 µm optional")),
    "led":   ((630, 410), (820, 540), "LED CONTOUR BACKLIGHT", ("8-ZONE", " programmable ring light")),
    "bolt":  ((440, 370), (700, 540), "18–195X MAGNIFICATION", ("", "industrial colour CCD camera")),
}
TAGS = {"thread": "AUTO EDGE DETECTION", "holes": "ONE-CLICK CIRCLE FITTING", "report": "INSTANT INSPECTION REPORT"}

F_T = E.font(E.F_BLACK, 30)
F_S = E.font(E.F_SEMI, 19)
F_M = E.font(r"C:\Windows\Fonts\consolab.ttf", 15)


# ---------------------------------------------------------------- sources
READERS = {}


def vframe(path, idx):
    r = READERS.get(path)
    if r is None:
        r = READERS[path] = E.Reader(path)
    if r.proc is not None and idx == r.pos - 1:
        return r._last
    return r.frame(idx)


HERO = None


def hero_frame(t, n):
    global HERO
    if HERO is None:
        HERO = Image.open("v2/stills/s_hero_v2.png").convert("RGB")
    z = 1.0 + 0.07 * (t / n)
    iw, ih = HERO.size
    cw, ch = iw / z, ih / z
    # push toward the lens/head (upper middle)
    cx, cy = iw * 0.47, ih * 0.42 + (ih * 0.5 - ih * 0.42) * (1 - t / n)
    box = (cx - cw / 2, max(0, cy - ch / 2), cx + cw / 2, max(0, cy - ch / 2) + ch)
    return HERO.crop(tuple(int(v) for v in box)).resize((W, H), Image.LANCZOS)


# ---------------------------------------------------------------- overlays
def hud(base, t, n):
    a = E.ease_out(t / 6) * (1 - E.ease_out((t - n + 5) / 5) if t > n - 5 else 1)
    if a <= 0:
        return
    o = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(o)
    m, L, c = 26, 34, (255, 255, 255, int(150 * a))
    for (x, y, sx, sy) in [(m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)]:
        d.line((x, y, x + sx * L, y), fill=c, width=2)
        d.line((x, y, x, y + sy * L), fill=c, width=2)
    d.text((W - 230, m + 8), "CRYSTAL VMM  ·  LIVE", font=F_M, fill=(255, 255, 255, int(120 * a)))
    rec = (t // 10) % 2 == 0
    d.ellipse((W - 250, m + 11, W - 240, m + 21), fill=(225, 30, 36, int(200 * a)) if rec else (0, 0, 0, 0))
    z = 41.0062 - t * 0.0011
    d.text((m + 8, H - m - 26), f"X 12.5148   Y -3.2207   Z {z:7.4f}", font=F_M, fill=(255, 255, 255, int(110 * a)))
    base.alpha_composite(o)


def callout(base, key, t, n):
    (tx, ty), (lx, ly), title, (val, rest) = CALL[key]
    out = 1 - E.ease_out((t - n + 6) / 5) if t > n - 6 else 1.0
    o = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(o)
    # target reticle
    ta = E.ease_out(t / 6) * out
    if ta > 0:
        r = 22 - 8 * E.back_out(t / 7)
        c = (255, 255, 255, int(235 * ta))
        d.ellipse((tx - r, ty - r, tx + r, ty + r), outline=c, width=2)
        d.ellipse((tx - 3, ty - 3, tx + 3, ty + 3), fill=(60, 255, 120, int(255 * ta)))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            d.line((tx + dx * (r + 4), ty + dy * (r + 4), tx + dx * (r + 12), ty + dy * (r + 12)), fill=c, width=2)
    # plate geometry
    tw = max(F_T.getlength(title), F_S.getlength(val + rest)) + 44
    ph = 86
    # elbow leader: target -> (elbow) -> plate edge
    ax = lx if tx < lx else lx + tw
    ay = ly + 30
    ex, ey = ax + (-40 if tx < lx else 40), ay
    pts = [(tx, ty), (ex, ey), (ax, ay)]
    lp = E.ease_out((t - 3) / 8)
    if lp > 0 and out > 0:
        segs = [(pts[0], pts[1]), (pts[1], pts[2])]
        lens = [np.hypot(b[0] - a[0], b[1] - a[1]) for a, b in segs]
        rem = lp * sum(lens)
        for (a, b), L in zip(segs, lens):
            if rem <= 0:
                break
            f = min(1, rem / L)
            d.line((a[0], a[1], a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), fill=(255, 255, 255, int(220 * out)), width=2)
            rem -= L
    # plate + text
    pa = E.ease_out((t - 8) / 7) * out
    if pa > 0:
        sl = (1 - E.ease_out((t - 8) / 9)) * (-24 if tx > lx else 24)
        x0 = lx + sl
        d.rounded_rectangle((x0, ly, x0 + tw, ly + ph), 8, fill=(8, 10, 12, int(185 * pa)))
        d.rectangle((x0, ly + 10, x0 + 4, ly + ph - 10), fill=RED + (int(255 * pa),))
        d.text((x0 + 22, ly + 10), title, font=F_T, fill=(255, 255, 255, int(255 * pa)))
        x = x0 + 22
        if val:
            d.text((x, ly + 52), val, font=F_S, fill=GREEN + (int(255 * pa),)); x += F_S.getlength(val)
        d.text((x, ly + 52), rest, font=F_S, fill=GREY + (int(255 * pa),))
    base.alpha_composite(o)


HERO_SPR = None


def hero_title(base, t, n):
    global HERO_SPR
    if HERO_SPR is None:
        g = np.zeros((H, W, 4), np.uint8)
        xs, ys = np.meshgrid(np.arange(W), np.arange(H))
        a = np.clip((ys - 330) / 390, 0, 1) * np.clip(1.25 - xs / 1000, 0, 1) * 230
        g[..., 3] = a.astype(np.uint8)
        HERO_SPR = (Image.fromarray(g, "RGBA"),
                    E.text_img("C R Y S T A L   ·   S I N C E   1 9 8 0", E.font(E.F_BLACK, 18), RED)[0],
                    E.text_img("VIDEO MEASURING", E.font(E.F_BLACK, 58), (255, 255, 255))[0],
                    E.text_img("MACHINES", E.font(E.F_BLACK, 58), GREEN)[0],
                    E.text_img("Non-contact optical metrology for the shop floor", E.font(E.F_SEMI, 21), (215, 220, 224))[0])
    grad, kick, l1, l2, sub = HERO_SPR
    base.alpha_composite(grad)
    for k, (spr, y, f0) in enumerate([(kick, 470, 2), (l1, 500, 5), (l2, 562, 9), (sub, 632, 14)]):
        a = E.ease_out((t - f0) / 8)
        E.paste(base, spr, 66 - 30 * (1 - a), y, a)


def tag(base, key, t):
    txt = TAGS[key]
    f = E.font(E.F_BLACK, 20)
    w = int(f.getlength(txt)) + 48
    a = E.ease_out((t - 4) / 7)
    if a <= 0:
        return
    o = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(o)
    x, y = W - 60 - w, 606
    d.rounded_rectangle((x, y, x + w, y + 44), 22, fill=(60, 255, 120, int(235 * a)))
    d.text((x + 24, y + 9), txt, font=f, fill=(8, 20, 12, int(255 * a)))
    base.alpha_composite(o)


def flash(img, f):
    for c in CUTS:
        k = f - c
        big = c in BIG_CUTS
        if (-3 <= k <= 2) if big else (0 <= k <= 1):
            s = (1 - abs(k + 0.5) / 3.5) if big else (0.45 if k == 0 else 0.15)
            a = np.asarray(img.convert("RGB")).astype(np.float32)
            if big:
                shift = int(60 * s) * (1 if k < 0 else -1)
                a = sum(np.roll(a, int(shift * i / 5), axis=1) for i in range(6)) / 6
            a = a + (255 - a) * (0.85 * s ** 1.5 if big else s)
            return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")
    return img


def screen_push(img, t, n):
    z = 1.0 + 0.035 * (t / n)
    cw, ch = W / z, H / z
    x0, y0 = (W - cw) / 2, (H - ch) / 2
    return img.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.LANCZOS)


def compose(f):
    for name, s, n, kind, src in TL:
        if s <= f < s + n:
            t = f - s
            break
    if kind == "video":
        base = Image.fromarray(vframe(src, t)).convert("RGBA")
        if name == "hook":
            E.draw_hook(base, t)
        else:
            hud(base, t, n)
            callout(base, name, t, n)
    elif kind == "still":
        base = hero_frame(t, n).convert("RGBA")
        hero_title(base, t, n)
    elif kind == "screen":
        base = screen_push(src(t, n), t, n).convert("RGBA")
        tag(base, name, t)
    else:
        base = E.draw_end(t)
    return flash(base, f)


def main():
    if sys.argv[1] == "preview":
        os.makedirs("v3/preview", exist_ok=True)
        for f in map(int, sys.argv[2:]):
            compose(f).convert("RGB").save(f"v3/preview/v3_{f:04d}.png")
            print("preview", f, f"{f / FPS:.2f}s")
        return
    out = sys.argv[2] if len(sys.argv) > 2 else "VMM_promo_v3_720p.mp4"
    cmd = [FF, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", "audio/music30_mix.wav", "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k",
           "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
           "-t", "30", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(TOTAL):
        p.stdin.write(compose(f).convert("RGB").tobytes())
        if f % 90 == 0:
            print("frame", f, flush=True)
    p.stdin.close(); p.wait()
    print("done", out, p.returncode)


if __name__ == "__main__":
    main()
