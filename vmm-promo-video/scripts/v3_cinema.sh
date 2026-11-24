#!/usr/bin/env bash
# v3: one 15s Cinema Studio 4.0 multi-shot, real grey/red-band unit, styled from the earlier 30s project.
# Usage: v3_cinema.sh [cost|run]
set -euo pipefail
read -r -d '' PROMPT <<'EOF' || true
Premium commercial product film of an industrial optical video measuring machine, six shots, smooth controlled cinematic motion, realistic, clean grey metrology laboratory with soft haze, matching the lighting, color grade and camera style of the reference video.
The machine is exactly the one in the reference images: tall light-grey rectangular camera head with a red vertical accent band on its side, long black zoom lens with a black ring light, black column with a black corrugated cable, rectangular black XY stage with rounded cylindrical front and back rails and a clear glass plate in a speckled black granite top, solid speckled black granite base on levelling feet, silver micrometer knob on the right front. Keep its geometry rigid and exact in every shot, no extra parts.
Shot 1 (0-2.5s): starts on the start frame; slow crane up from the glass stage, revealing the full light-grey camera head with its red band.
Shot 2 (2.5-5s): low macro tracking shot along the rounded black stage rail as the XY stage glides smoothly and precisely across the granite base.
Shot 3 (5-7.5s): macro inside the machine base: a precision ground ball screw rotating, a steel carriage sliding smoothly along a hardened linear guide rail, fine machined metal, shallow depth of field.
Shot 4 (7.5-10s): top-down view through the glass plate: the circular array of white bottom LEDs in the granite switches on and bright clean light rises up through the glass.
Shot 5 (10-12.5s): a small precision-machined steel threaded shaft rests on the backlit glass stage, its thread profile turning into a crisp dark silhouette against the light.
Shot 6 (12.5-15s): side macro: the black zoom lens descends smoothly along the Z axis toward the threaded part and its ring light glows on as it reaches focus.
Hard cuts between shots, steady motion, razor-sharp focus, true-to-life materials.
No text, no labels, no logos, no watermark, no screens, no human hands, no deformed geometry, no morphing, no flicker.
EOF
R=v2/ref; S=v2/stills
ARGS=(cinematic_studio_video_4_0 --prompt "$PROMPT" --mode omni_reference
  --start-image $S/s_hero_v2.png
  --image $S/s2_stage.png --image $S/s_led_v2.png --image $S/s4_load.png --image $S/s5_zfocus.png
  --image $R/real_full_crop.png --image $R/real_55.png
  --video v3/src/cinema30.mp4
  --duration 15 --resolution 720p --aspect_ratio 16:9 --generate_audio false --bitrate_mode high)
if [ "${1:-cost}" = cost ]; then higgsfield generate cost "${ARGS[@]}"; else higgsfield generate create "${ARGS[@]}" --wait --wait-timeout 40m --json; fi
