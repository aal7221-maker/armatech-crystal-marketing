"""Crisp, layered Crystal logo + reveal animation (no AI).

Layers are rebuilt from the best available raster: upsampled 4x, softly thresholded
(clean anti-aliased contours), then split into frame / script / SINCE 1980 / dashes.

logo_plate(t, logo_w) -> RGBA white rounded plate with the logo animated at frame t.
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

SRC = "v4/src/logo_src2.png"
UP = 4
RED = np.array([226, 24, 30], np.float32)
GREY = np.array([72, 74, 78], np.float32)
_L = None


def _smooth_mask(score, blur):
    """score in 0..1 at high res -> crisp anti-aliased mask."""
    s = ndimage.gaussian_filter(score, blur)
    return np.clip((s - 0.5) * 6 + 0.5, 0, 1)


def build():
    global _L
    if _L is not None:
        return _L
    im = Image.open(SRC).convert("RGB")
    a0 = np.asarray(im).astype(np.float32)
    redness = (a0[..., 0] - np.maximum(a0[..., 1], a0[..., 2])) / 255.0
    # continuous coverage scores (keep the source anti-aliasing instead of a hard cutoff)
    red = np.clip((redness - 0.10) / 0.35, 0, 1)
    lum = a0.mean(axis=2); sat = a0.max(axis=2) - a0.min(axis=2)
    grey = np.clip((205 - lum) / 110, 0, 1) * (sat < 60)
    ys, xs = np.where((red + grey) > 0.5)
    pad = 8
    x0, y0, x1, y1 = xs.min() - pad, ys.min() - pad, xs.max() + pad, ys.max() + pad
    red, grey = red[y0:y1, x0:x1], grey[y0:y1, x0:x1]
    h, w = red.shape
    up = lambda m: np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize((w * UP, h * UP), Image.LANCZOS)).astype(np.float32) / 255.0
    R = _smooth_mask(up(red), 3.6)
    G = _smooth_mask(up(grey), 3.2)
    # split red: frame = component with the widest bbox, rest = script
    lab, n = ndimage.label(R > 0.5)
    objs = ndimage.find_objects(lab)
    widths = [(sl[1].stop - sl[1].start) * (sl[0].stop - sl[0].start) for sl in objs]
    fid = int(np.argmax(widths)) + 1
    fmask = ndimage.binary_dilation(lab == fid, iterations=3)
    frame = R * fmask
    script = R * (~fmask)
    # split grey: dashes = wide, short components; text = rest
    glab, gn = ndimage.label(G > 0.5)
    dash = np.zeros_like(G, bool)
    for i, sl in enumerate(ndimage.find_objects(glab), 1):
        hh, ww = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if ww > 4 * hh:
            dash |= glab == i
    dash = ndimage.binary_dilation(dash, iterations=3)
    text = G * (~dash)
    dashes = G * dash
    H, W = R.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    fy, fx = np.where(frame > 0.5)
    fcx, fcy = fx.mean(), fy.mean()
    ang = (np.degrees(np.arctan2(yy - fcy, xx - fcx)) + 180 + 45) % 360 / 360.0   # 0 at top-left corner, clockwise
    ty, tx = np.where(text > 0.5)
    tcx = tx.mean()
    _L = dict(frame=frame, script=script, text=text, dashes=dashes, ang=ang, xx=xx, yy=yy,
              tcx=tcx, W=W, H=H, sx=(script > 0.5).any(axis=0).nonzero()[0])
    return _L


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def logo_layer(t):
    """Full-res RGBA logo at frame t (transparent background)."""
    L = build()
    W, H, xx, yy = L["W"], L["H"], L["xx"], L["yy"]
    # 1) frame draws on clockwise from the top-left corner (frames 4..24)
    p = ease((t - 4) / 20)
    fa = L["frame"] * np.clip((p * 1.04 - L["ang"]) / 0.04, 0, 1)
    # 2) script wipes on left->right along its italic slant (frames 12..34)
    sx0, sx1 = L["sx"].min(), L["sx"].max()
    q = ease((t - 12) / 22)
    edge = sx0 - 160 + (sx1 - sx0 + 160 + 420) * q        # overshoots so the slanted edge fully clears
    slant = (yy - H * 0.45) * -0.25
    sa = L["script"] * np.clip((edge - (xx + slant)) / 80 + 1, 0, 1)
    # 3) dashes extend outward from the text centre (frames 28..40)
    r = ease((t - 28) / 12)
    dist = np.abs(xx - L["tcx"])
    da = L["dashes"] * np.clip((r * W * 0.55 - dist) / 30 + 1, 0, 1) * (r > 0)
    # 4) SINCE 1980 rises + fades in (frames 30..42)
    s = ease((t - 30) / 12)
    shift = int((1 - s) * 40)
    ta = np.roll(L["text"], shift, axis=0) * s
    red_a = np.clip(fa + sa, 0, 1)
    grey_a = np.clip(da + ta, 0, 1)
    rgb = np.zeros((H, W, 3), np.float32)
    alpha = np.clip(red_a + grey_a, 0, 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        wr = np.where(alpha > 0, red_a / np.maximum(red_a + grey_a, 1e-6), 0)[..., None]
    rgb = RED * wr + GREY * (1 - wr)
    # 5) shine sweep across the red (frames 44..60), plus a bright pen-tip on the frame draw
    sh = (t - 44) / 16
    if 0 < sh < 1:
        band = np.exp(-(((xx + yy * 0.6) - (sh * (W + H) * 1.1 - H * 0.3)) / 70.0) ** 2)
        rgb = rgb + (255 - rgb) * (band * red_a * 0.75)[..., None]
    out = np.dstack([np.clip(rgb, 0, 255), alpha * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def logo_plate(t, logo_w, plate_alpha=1.0):
    """White rounded plate (grows open from a line, frames 0..8) with the animated logo."""
    lg = logo_layer(t)
    lw = int(logo_w); lh = int(lg.height * lw / lg.width)
    lg = lg.resize((lw, lh), Image.LANCZOS)
    padx, pady = int(lw * 0.09), int(lh * 0.12)
    pw, ph = lw + 2 * padx, lh + 2 * pady
    g = ease(t / 8)
    cur_h = max(4, int(ph * g))
    plate = Image.new("RGBA", (pw + 80, ph + 80), (0, 0, 0, 0))
    # soft shadow
    sh = Image.new("RGBA", plate.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((40, 40 + (ph - cur_h) // 2 + 10, 40 + pw, 40 + (ph + cur_h) // 2 + 10),
                                         int(min(28, cur_h / 2)), fill=(0, 0, 0, int(150 * plate_alpha)))
    plate.alpha_composite(sh.filter(ImageFilter.GaussianBlur(16)))
    body = Image.new("RGBA", plate.size, (0, 0, 0, 0))
    ImageDraw.Draw(body).rounded_rectangle((40, 40 + (ph - cur_h) // 2, 40 + pw, 40 + (ph + cur_h) // 2),
                                           int(min(28, cur_h / 2)), fill=(255, 255, 255, int(255 * plate_alpha)))
    plate.alpha_composite(body)
    if t > 3:
        plate.alpha_composite(lg, (40 + padx, 40 + pady))
    return plate


if __name__ == "__main__":
    import os
    os.makedirs("v4/preview", exist_ok=True)
    frames = [6, 14, 22, 30, 38, 52, 70]
    tiles = [logo_plate(f, 520) for f in frames]
    W = max(t.width for t in tiles); H = max(t.height for t in tiles)
    sheet = Image.new("RGB", (W * 4, H * 2), (8, 10, 12))
    for k, tl in enumerate(tiles):
        sheet.paste(tl, ((k % 4) * W, (k // 4) * H), tl)
    sheet.save("v4/preview/logo_anim_sheet.png")
    logo_plate(80, 900).save("v4/preview/logo_final_big.png")
    print("ok", logo_layer(80).size)
