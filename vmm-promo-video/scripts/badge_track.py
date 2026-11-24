"""Track the camera head through the opener orbit and pin the crisp Crystal logo badge onto its front face.

1) LK optical flow on corner features inside the head region -> per-frame homography (frame 0 -> t),
   smoothed over time.
2) Badge quad defined on frame 0, warped per frame; logo layer composited with matched lighting + softness.
Writes v5hd/seg/opener_logo.mp4 (1920x1080, same frame count) and v6/track/check_*.png.
"""
import os, subprocess, sys
import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import logo_anim as LA

FF = r"C:\Users\lunaw\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
FR = sorted(f for f in os.listdir("v6/track") if f.startswith("f_"))
frames = [cv2.imread(f"v6/track/{f}") for f in FR]
N = len(frames)
H_, W_ = frames[0].shape[:2]

# head region on frame 0 (x 850-1085, y 35-425)
ROI = (850, 35, 1085, 425)
BADGE = np.float32([[978, 92], [1052, 92], [1052, 142], [978, 142]])   # on the wide face, left of the red band

g0 = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
mask = np.zeros_like(g0); mask[ROI[1]:ROI[3], ROI[0]:ROI[2]] = 255
p0 = cv2.goodFeaturesToTrack(g0, maxCorners=400, qualityLevel=0.005, minDistance=5, mask=mask, blockSize=5)
print("features", len(p0))

Hs = [np.eye(3)]
prev, pts_prev, pts0 = g0, p0, p0.copy()
lk = dict(winSize=(25, 25), maxLevel=4, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 40, 0.01))
for i in range(1, N):
    g = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
    p1, st, _ = cv2.calcOpticalFlowPyrLK(prev, g, pts_prev, None, **lk)
    pb, stb, _ = cv2.calcOpticalFlowPyrLK(g, prev, p1, None, **lk)               # forward-backward check
    fb = np.linalg.norm(pts_prev - pb, axis=2).ravel()
    good = (st.ravel() == 1) & (stb.ravel() == 1) & (fb < 0.8)
    pts_prev, pts0 = p1[good], pts0[good]
    Hm, inl = cv2.findHomography(pts0, pts_prev, cv2.RANSAC, 2.0)
    Hs.append(Hm)
    prev = g
print("features left", len(pts0))

# geometric anchors (more stable than point tracking on the smooth head):
# seam = edge between the two head faces, xr = left edge of the red band, yt/yb = red band top/bottom
geo = np.load("v6/track/geo2.npy")               # i, outer, seam, xr, yt, yb, ...
corners = []
for i in range(N):
    _, _, seam, xr, yt, yb = geo[i][:6]
    fw = xr - seam
    w = 0.62 * fw
    h = w / 1.43
    cx = seam + 0.49 * fw
    top = yt + 0.10 * (yb - yt)
    corners.append([[cx - w / 2, top], [cx + w / 2, top], [cx + w / 2, top + h], [cx - w / 2, top + h]])
corners = np.array(corners, np.float32)
k = 9
ker = np.ones(k) / k
sm = corners.copy()
for c in range(4):
    for d in range(2):
        x = np.pad(corners[:, c, d], (k // 2, k // 2), mode="edge")
        sm[:, c, d] = np.convolve(x, ker, mode="valid")

# logo layer: crisp, finished state, on a subtle white sticker plate
lg = LA.logo_layer(80)                                    # RGBA, transparent bg
lw, lh = lg.size
pad_x, pad_y = int(lw * 0.06), int(lh * 0.08)
badge = Image.new("RGBA", (lw + 2 * pad_x, lh + 2 * pad_y), (255, 255, 255, 0))
from PIL import ImageDraw
ImageDraw.Draw(badge).rounded_rectangle((0, 0, badge.width - 1, badge.height - 1), int(lh * 0.06), fill=(250, 250, 250, 225))
badge.alpha_composite(lg, (pad_x, pad_y))
B = np.asarray(badge).astype(np.float32) / 255.0
bh, bw = B.shape[:2]
src = np.float32([[0, 0], [bw, 0], [bw, bh], [0, bh]])

os.makedirs("v6/track", exist_ok=True)
out = "v5hd/seg/opener_logo.mp4"
p = subprocess.Popen([FF, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W_}x{H_}", "-r", "30",
                      "-i", "-", "-c:v", "libx264", "-crf", "10", "-preset", "fast", "-pix_fmt", "yuv420p", out],
                     stdin=subprocess.PIPE)
for i in range(N):
    fr = frames[i].astype(np.float32) / 255.0
    M = cv2.getPerspectiveTransform(src, sm[i].astype(np.float32))
    warped = cv2.warpPerspective(B, M, (W_, H_), flags=cv2.INTER_LANCZOS4, borderValue=(0, 0, 0, 0))
    warped = cv2.GaussianBlur(warped, (0, 0), 0.55)                  # match footage softness
    a = warped[..., 3:4]
    rgb = warped[..., :3][..., ::-1]                                  # RGBA(PIL) -> BGR
    # light matching: modulate by the face's own local brightness relative to its mean
    lum = cv2.GaussianBlur(cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0, (0, 0), 9)
    x0, y0 = sm[i].min(axis=0).astype(int); x1, y1 = sm[i].max(axis=0).astype(int)
    ref = float(lum[y0:y1, x0:x1].mean()) if (x1 > x0 and y1 > y0) else 0.85
    shade = np.clip(lum / max(ref, 1e-3), 0.85, 1.08)[..., None] * (0.92 + 0.08 * ref)
    comp = np.nan_to_num(fr * (1 - a) + (rgb * shade) * a)
    img = (np.clip(comp, 0, 1) * 255).astype(np.uint8)
    p.stdin.write(img.tobytes())
    if i in (0, N // 2, N - 1):
        cv2.imwrite(f"v6/track/check_{i:03d}.png", img[0:520, 760:1240])
p.stdin.close(); p.wait()
print("wrote", out, N, "frames")
