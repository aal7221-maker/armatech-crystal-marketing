"""v4 edit: ~48s readable-pace promo (1280x720 @30fps): full-machine opener, slower callouts,
software screens, 5-series lineup, end card with Armatech contact.

python edit_v4.py preview f1 f2 ...   -> v4/preview/v4_XXXX.png
python edit_v4.py render [out.mp4]    -> VMM_promo_v4_720p.mp4
"""
import os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
import edit as E
import screens as S
import edit_v3 as V3
import logo_anim as LA

FF, W, H, FPS = E.FF, 1280, 720, 30
GREEN, RED = E.GREEN, E.RED

# bigger, longer-held callout text
V3.F_T = E.font(E.F_BLACK, 34)
V3.F_S = E.font(E.F_SEMI, 22)
V3.CALL["zfocus"] = ((640, 330), (70, 500), "CNC Z-AXIS + AUTO FOCUS", ("", "semi-automatic & fully automatic models"))
V3.CALL["stage"] = ((560, 210), (70, 500), "PRECISION XY STAGE", ("", "on a solid granite base"))
V3.CALL["knob"] = ((790, 460), (70, 500), "FINE MICROMETER CONTROL", ("", "manual X / Y drive"))
V3.CALL["screw"] = ((1000, 240), (70, 500), "PRECISION DRIVE MECHANICS", ("SERVO CNC", "  X / Y / Z on fully automatic"))
V3.CALL["scale"] = ((660, 490), (720, 110), "LINEAR SCALE", ("0.5 µm", "  resolution  ·  0.1 µm optional"))
V3.CALL["led"] = ((630, 410), (770, 520), "LED CONTOUR BACKLIGHT", ("8-ZONE", "  programmable ring light"))
V3.CALL["bolt"] = ((440, 370), (650, 520), "18–195X MAGNIFICATION", ("", "industrial colour CCD camera"))

SEGS = [  # name, seconds, kind, source
    ("opener", 5.0, "opener", "v4/seg/opener.mp4"),
    ("zfocus", 3.0, "video", "v4/seg/zfocus.mp4"),
    ("stage", 3.5, "video", "v4/seg/stage.mp4"),
    ("knob", 3.0, "video", "v4/seg/knob.mp4"),
    ("screw", 3.5, "video", "v4/seg/screw.mp4"),
    ("scale", 3.5, "video", "v4/seg/scale.mp4"),
    ("led", 3.0, "video", "v4/seg/led.mp4"),
    ("bolt", 3.0, "video", "v4/seg/bolt.mp4"),
    ("thread", 4.0, "screen", S.screen_thread),
    ("holes", 3.5, "screen", S.screen_holes),
    ("report", 2.5, "screen", S.screen_report),
    ("lineup", 4.5, "lineup", None),
    ("end", 7.5, "end", None),
]
TL, _f = [], 0
for name, secs, kind, src in SEGS:
    n = int(round(secs * FPS)); TL.append((name, _f, n, kind, src)); _f += n
TOTAL = _f
CUTS = [s for _, s, _, _, _ in TL[1:]]
BIG = {TL[1][1], TL[8][1], TL[11][1], TL[12][1]}


# ---------------------------------------------------------------- opener: hook then title
def draw_opener(base, t, n):
    # hook words 0..~2.7s, then fade; title from 2.9s
    if t < 84:
        a_out = 1 - E.ease_out((t - 74) / 10) if t > 74 else 1
        dark = Image.new("RGBA", (W, H), (0, 0, 0, int(110 * a_out)))
        base.alpha_composite(dark)
        lh, y0 = 122, H // 2 - 122
        for k, ((spr, pad), f0) in enumerate(E.HOOK_SPR):
            lt = (t - (8 + k * 16)) / 7.0
            if lt < 0:
                continue
            s = 1.45 - 0.45 * E.back_out(lt)
            E.paste(base, spr, W // 2, y0 + k * lh, E.ease_out(lt * 1.6) * a_out, s, "mm")
    if t >= 86:
        V3.hero_title(base, t - 86, n - 86)


# ---------------------------------------------------------------- lineup
SERIES = [
    ("ref_manual.png", "MANUAL", ["AA-9011M", "AA-9012M", "AA-9013M"]),
    ("ref_semiauto.png", "SEMI-AUTOMATIC", ["AA-9021SA", "AA-9022SA", "AA-9023SA"]),
    ("ref_fullauto.png", "FULLY AUTOMATIC", ["AA-9031A", "AA-9032A", "AA-9033A"]),
    ("ref_cabinet.png", "WITH CABINET", ["AA-9041AC", "AA-9042AC", "AA-9043AC", "AA-9044AC"]),
    ("ref_vms.png", "VMS SERIES", ["AA-9051V", "AA-9052V", "AA-9053V"]),
]
CARD_W, CARD_H, GAP = 224, 400, 18
LINEUP = None


def make_cards():
    cards = []
    fs, fm, fn = E.font(E.F_BLACK, 17), E.font(E.F_SEMI, 16), E.font(E.F_BLACK, 15)
    for k, (img, name, models) in enumerate(SERIES):
        c = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
        m = Image.new("L", (CARD_W, CARD_H), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, CARD_W - 1, CARD_H - 1), 16, fill=255)
        body = Image.new("RGBA", (CARD_W, CARD_H), (255, 255, 255, 255))
        d = ImageDraw.Draw(body)
        # photo area
        ph = Image.open(img).convert("RGB")
        a = np.asarray(ph).copy(); a[a.min(axis=2) > 232] = 255; ph = Image.fromarray(a)
        ph.thumbnail((CARD_W - 28, 236), Image.LANCZOS)
        body.paste(ph, ((CARD_W - ph.width) // 2, 14 + (236 - ph.height) // 2))
        # text panel
        d.rectangle((0, 260, CARD_W, CARD_H), fill=(18, 21, 24))
        d.rectangle((0, 260, CARD_W, 264), fill=RED)
        d.text((16, 274), f"0{k + 1}", font=fn, fill=RED)
        d.text((44, 272), name, font=fs, fill=(255, 255, 255))
        for j, mo in enumerate(models):
            d.text((16, 306 + j * 21), mo, font=fm, fill=(205, 212, 218))
        c.paste(body, (0, 0), m)
        cards.append(c)
    return cards


def draw_lineup(t, n):
    global LINEUP
    if LINEUP is None:
        bg = np.zeros((H, W, 3), np.float32); bg[:] = (10, 12, 14)
        yy, xx = np.mgrid[0:H, 0:W]
        d = np.sqrt(((xx - W / 2) / 760) ** 2 + ((yy - H * 0.55) / 420) ** 2)
        bg += (np.clip(1 - d, 0, 1) ** 2)[..., None] * np.array([10, 34, 18])
        LINEUP = (Image.fromarray(bg.astype(np.uint8)).convert("RGBA"), make_cards(),
                  E.text_img("AVAILABLE MODELS", E.font(E.F_BLACK, 44), (255, 255, 255))[0],
                  E.text_img("5 series  ·  16 models  ·  available now", E.font(E.F_SEMI, 22), GREEN)[0])
    bg, cards, h1, h2 = LINEUP
    fr = bg.copy()
    a = E.ease_out(t / 8)
    E.paste(fr, h1, W // 2, 70, a, 1.0, "mm")
    E.paste(fr, h2, W // 2, 118, E.ease_out((t - 5) / 8), 1.0, "mm")
    total_w = 5 * CARD_W + 4 * GAP
    x0, y0 = (W - total_w) // 2, 170
    for k, c in enumerate(cards):
        lt = (t - 8 - k * 5) / 10
        if lt <= 0:
            continue
        dy = (1 - E.ease_out(lt)) * 80
        # soft shadow
        sh = Image.new("RGBA", (CARD_W + 40, CARD_H + 40), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((20, 26, CARD_W + 20, CARD_H + 26), 16, fill=(0, 0, 0, 160))
        sh = sh.filter(ImageFilter.GaussianBlur(12))
        E.paste(fr, sh, x0 + k * (CARD_W + GAP) - 20, y0 + dy - 20, E.ease_out(lt))
        E.paste(fr, c, x0 + k * (CARD_W + GAP), y0 + dy, E.ease_out(lt * 1.4))
    return fr


# ---------------------------------------------------------------- end card with contact
CONTACT = ["Armatech Associates",
           "W-174, A 'S' Block, M.I.D.C, Bhosari,",
           "Pune 411026",
           "GST No. 27AACFA6934B1ZT",
           "Cell: 09371013689",
           "Email: armatech@gmail.com"]
END = None


def make_end():
    bg = np.zeros((H, W, 3), np.float32); bg[:] = (6, 8, 10)
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W * 0.3) / 640) ** 2 + ((yy - H / 2) / 420) ** 2)
    bg += (np.clip(1 - d, 0, 1) ** 2)[..., None] * np.array([8, 40, 20])
    bg += (((xx % 40 == 0) | (yy % 40 == 0)).astype(np.float32) * 6)[..., None] * np.array([0.4, 1, 0.6])
    bgi = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).convert("RGBA")

    left = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cx = 360
    final_plate_h = LA.logo_plate(70, LOGO_FINAL_W).height - 80      # body height (plate image has 40px shadow margin)
    dl = ImageDraw.Draw(left)
    ft = E.font(E.F_BLACK, 46)
    parts = [("5 SERIES ", (255, 255, 255)), ("·", GREEN), (" 16 MODELS", (255, 255, 255))]
    tw = sum(ft.getlength(p) for p, _ in parts); x = cx - tw / 2; ty = LOGO_FINAL_TOP + final_plate_h + 30
    for p, c in parts:
        dl.text((x, ty), p, font=ft, fill=c); x += ft.getlength(p)
    fs = E.font(E.F_SEMI, 20)
    for j, s in enumerate(["Video Measuring Machines", "accuracy from 2 µm  ·  up to 195X"]):
        dl.text((cx - fs.getlength(s) / 2, ty + 66 + j * 28), s, font=fs, fill=(200, 206, 210))
    btn_y = ty + 140

    right = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(right)
    px0, py0, pw, phh = 700, 170, 520, 360
    dr.rounded_rectangle((px0, py0, px0 + pw, py0 + phh), 18, fill=(255, 255, 255, 18), outline=(255, 255, 255, 60), width=1)
    dr.rectangle((px0, py0 + 24, px0 + 5, py0 + 84), fill=RED)
    dr.text((px0 + 30, py0 + 26), "CONTACT", font=E.font(E.F_BLACK, 18), fill=RED)
    dr.text((px0 + 30, py0 + 52), CONTACT[0], font=E.font(E.F_BLACK, 32), fill=(255, 255, 255))
    fl = E.font(E.F_SEMI, 21)
    y = py0 + 112
    for line in CONTACT[1:3]:
        dr.text((px0 + 30, y), line, font=fl, fill=(214, 220, 224)); y += 30
    y += 14
    dr.line((px0 + 30, y, px0 + pw - 30, y), fill=(255, 255, 255, 50), width=1); y += 20
    fb = E.font(E.F_BLACK, 24)
    for line in CONTACT[4:]:
        k, v = line.split(": ", 1)
        dr.text((px0 + 30, y), k.upper(), font=E.font(E.F_BLACK, 15), fill=GREEN)
        dr.text((px0 + 110, y - 6), v, font=fb, fill=(255, 255, 255)); y += 46
    dr.text((px0 + 30, y + 4), CONTACT[3], font=E.font(E.F_SEMI, 17), fill=(150, 158, 166))
    return bgi, left, right, btn_y


LOGO_INTRO = 62          # frames of centred logo animation
LOGO_MOVE = 20           # frames to glide into the end-card position
LOGO_BIG_W, LOGO_FINAL_W, LOGO_FINAL_TOP = 600, 300, 86
_PLATES = {}


def plate_at(t_anim, w):
    key = (min(t_anim, 70), int(w))
    if key[0] >= 70 and key in _PLATES:
        return _PLATES[key]
    p = LA.logo_plate(key[0], key[1])
    if key[0] >= 70:
        _PLATES[key] = p
    return p


def draw_end(t):
    global END
    if END is None:
        END = make_end() + E.make_button()
    bgi, left, right, btn_y, bglow, btn = END
    fr = bgi.copy()
    # --- logo: animate centred, then glide to its slot on the left
    m = E.ease_out((t - LOGO_INTRO) / LOGO_MOVE) if t > LOGO_INTRO else 0.0
    m = m * m * (3 - 2 * m)
    w = LOGO_BIG_W + (LOGO_FINAL_W - LOGO_BIG_W) * m
    pl = plate_at(t, w)
    body_h = pl.height - 80
    cx = W / 2 + (360 - W / 2) * m
    top_big = (H - body_h) / 2
    top = top_big + (LOGO_FINAL_TOP - top_big) * m
    fr.alpha_composite(pl, (int(cx - pl.width / 2), int(top - 40)))
    t = t - (LOGO_INTRO + LOGO_MOVE)          # rest of the card starts after the logo lands
    if t < 0:
        return fr
    sweep = E.ease_out(t / 26.0)
    sx = int(-40 + sweep * (W + 80))
    if sx > 0:
        m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).rectangle((0, 0, min(sx, W), H), fill=255)
        rev = Image.new("RGBA", (W, H), (0, 0, 0, 0)); rev.paste(left, (0, 0), m)
        E.paste(fr, rev, 0, 0, E.ease_out((t - 2) / 16))
    ra = E.ease_out((t - 18) / 12)
    E.paste(fr, right, 30 * (1 - ra), 0, ra)
    if t < 34:
        line = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(line)
        for k in range(60):
            ld.line([(sx - k, 0), (sx - k, H)], fill=GREEN + (int(90 * (1 - k / 60) ** 2),))
        ld.rectangle((sx - 1, 0, sx + 2, H), fill=(200, 255, 215, 255))
        E.paste(fr, line, 0, 0, 1 - E.ease_out((t - 26) / 8) if t > 26 else 1)
    bt = (t - 30) / 9.0
    if bt > 0:
        import math
        sc = 0.6 + 0.4 * E.back_out(bt)
        pulse = 0.55 + 0.45 * (0.5 + 0.5 * math.sin((t - 40) / 30 * 2 * math.pi)) if t > 40 else E.ease_out(bt)
        cx, cy = 360, btn_y + btn.height // 2
        E.paste(fr, bglow, cx, cy, pulse * E.ease_out(bt), sc, "mm")
        E.paste(fr, btn, cx, cy, E.ease_out(bt * 1.5), sc, "mm")
    return fr


# ---------------------------------------------------------------- compose
def flash(img, f):
    for c in CUTS:
        k = f - c
        big = c in BIG
        if (-3 <= k <= 2) if big else (0 <= k <= 1):
            s = (1 - abs(k + 0.5) / 3.5) if big else (0.35 if k == 0 else 0.1)
            a = np.asarray(img.convert("RGB")).astype(np.float32)
            if big:
                shift = int(50 * s) * (1 if k < 0 else -1)
                a = sum(np.roll(a, int(shift * i / 5), axis=1) for i in range(6)) / 6
            a = a + (255 - a) * (0.8 * s ** 1.5 if big else s)
            return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")
    return img


def compose(f):
    for name, s, n, kind, src in TL:
        if s <= f < s + n:
            t = f - s; break
    if kind == "opener":
        base = Image.fromarray(V3.vframe(src, t)).convert("RGBA")
        draw_opener(base, t, n)
    elif kind == "video":
        base = Image.fromarray(V3.vframe(src, t)).convert("RGBA")
        V3.hud(base, t, n)
        V3.callout(base, name, t, n)
    elif kind == "screen":
        base = V3.screen_push(src(t, n), t, n).convert("RGBA")
        V3.tag(base, name, t)
    elif kind == "lineup":
        base = draw_lineup(t, n)
    else:
        base = draw_end(t)
    return flash(base, f)


def main():
    if sys.argv[1] == "preview":
        os.makedirs("v4/preview", exist_ok=True)
        for f in map(int, sys.argv[2:]):
            compose(f).convert("RGB").save(f"v4/preview/v4_{f:04d}.png")
            print("preview", f, f"{f / FPS:.2f}s")
        return
    out = sys.argv[2] if len(sys.argv) > 2 else "VMM_promo_v4_720p.mp4"
    dur = TOTAL / FPS
    cmd = [FF, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", "audio/music_v4_mix.wav", "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k",
           "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
           "-t", f"{dur:.3f}", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(TOTAL):
        p.stdin.write(compose(f).convert("RGB").tobytes())
        if f % 150 == 0:
            print("frame", f, flush=True)
    p.stdin.close(); p.wait()
    print("done", out, p.returncode, f"{dur:.2f}s")


if __name__ == "__main__":
    main()
