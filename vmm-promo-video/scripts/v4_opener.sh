#!/usr/bin/env bash
# v4 opener: 5s Cinema Studio 4.0 slow orbit of the full machine. Usage: v4_opener.sh [cost|run]
set -euo pipefail
read -r -d '' PROMPT <<'EOF' || true
Premium commercial product film, single continuous shot: a slow, smooth, steady orbital camera move of about 25 degrees around the complete industrial video measuring machine from the start frame, keeping the entire machine in frame from the top of the camera head to the levelling feet, subtle slow push-in, soft studio key light gliding across the light-grey head and the polished granite, clean bright metrology room softly out of focus, matching the realistic lighting and color grade of the reference video.
The machine stays exactly as in the start frame and reference images: light-grey rectangular camera head with a red accent band on its side face, black zoom lens, black column with black corrugated cable, black XY stage with rounded cylindrical rails and a glass plate, small silver knob, speckled black granite base on four levelling feet. Rigid geometry, nothing moves on the machine, no extra parts.
No text, no labels, no logos, no watermark, no people, no hands, no morphing, no flicker.
EOF
ARGS=(cinematic_studio_video_4_0 --prompt "$PROMPT" --mode omni_reference
  --start-image v2/stills/s_opener.png
  --image v2/stills/s_hero_v2.png --image v2/ref/real_full_crop.png
  --video v3/src/cinema30.mp4
  --duration 5 --resolution 720p --aspect_ratio 16:9 --generate_audio false --bitrate_mode high)
if [ "${1:-cost}" = cost ]; then higgsfield generate cost "${ARGS[@]}"; else higgsfield generate create "${ARGS[@]}" --wait --wait-timeout 30m --json; fi
