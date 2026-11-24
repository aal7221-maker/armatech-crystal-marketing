#!/usr/bin/env bash
# Step 2: 5 start-frame stills. Usage: stills.sh <index 1-5> [cost|run]
set -euo pipefail
STYLE="Cinematic product hero shot of this exact video measuring machine, dark premium metrology lab, black reflective floor, volumetric haze, glowing neon-green LED ring light under the camera lens, green light spilling across the glass stage, rim light on the brushed-aluminium column, shallow depth of field, ultra-detailed, commercial ad photography, no text, no labels, no logos."
KEEP="Keep the machine's exact shape, proportions and parts from the reference photo: same column, camera head, stage and base, no added parts. No text, no labels, no logos, no watermark."
NAMES=(x manual semiauto fullauto cabinet vms)
CAMS=(x
 "Camera: low-angle three-quarter hero view, machine towering against the dark lab."
 "Camera: tight close-up of the camera lens and the glowing green ring light above the glass stage, the column softly out of focus behind."
 "Camera: clean side profile of the whole machine, a laser-thin green scan line glowing across the glass stage."
 "Camera: wide shot of the full machine standing on its cabinet, green glow rising from below the cabinet onto the floor."
 "Camera: clean elevated top-down three-quarter view of the white-bodied machine, cool white light mixed with neon green.")
CLOSE=(x x
 "Camera: extreme macro close-up of the objective lens and the glowing neon-green LED ring light, the green ring reflected in the glass stage just below, the rest of the machine melted into dark bokeh. Lens fills most of the frame."
 "Camera: low macro shot at stage level: the lens hovering just above a small precision-machined metal part lying on the glass stage, a razor-thin bright green scan line crossing the part, the column out of focus above."
 "Camera: close-up detail of the cabinet's front control panel with its small green and red buttons and the edge of the black stage above, green under-glow on the cabinet, background in deep bokeh."
 "Camera: close-up detail of the white column, the black focus handwheel and the lens with its green ring light, cool white rim light with green accents, very shallow depth of field.")
i=$1; mode=${2:-cost}; v=${3:-}
CAM="${CAMS[$i]}"; [ "$v" = close ] && CAM="${CLOSE[$i]}"
ARGS=(gpt_image_2_6 --prompt "$STYLE $CAM $KEEP" --image "ref_${NAMES[$i]}.png" --aspect_ratio 16:9 --resolution 2k --quality xhigh)
if [ "$mode" = cost ]; then higgsfield generate cost "${ARGS[@]}"; else higgsfield generate create "${ARGS[@]}" --wait --json; fi
