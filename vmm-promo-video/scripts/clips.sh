#!/usr/bin/env bash
# Step 3: animate stills. Usage: clips.sh <index 1-5> [cost|run]
set -euo pipefail
KEEP="The machine stays rigid and exactly as in the start frame: same column, camera head, stage and base, no new parts, no morphing. Smooth, slow, premium commercial camera move. No text, no labels, no logos, no watermark."
IMGS=(x stills/still_1_manual.png stills/still_2_semiauto_closeup.png stills/still_3_fullauto.png stills/still_4_cabinet_closeup.png stills/still_5_vms_closeup.png)
MOVES=(x
 "Slow push-in toward the machine from a low angle, haze drifting through the green light; the green LED ring under the lens pulses brighter once, then settles."
 "Very slow macro push-in on the lens and green ring light; the green ring pulses brighter once and its reflection in the glass stage glows; floating dust particles in the light."
 "Slow sideways dolly along the machine's side profile; a thin green light beam sweeps across the glass stage once; the ring light pulses once."
 "Slow crane up from the cabinet control panel toward the stage edge; green under-glow pulses once; haze drifting."
 "Slow arcing orbit around the lens and focus handwheel; the green ring light pulses once; cool white rim light glints on the column.")
i=$1; mode=${2:-cost}
ARGS=(seedance_2_0_mini --prompt "${MOVES[$i]} $KEEP" --start-image "${IMGS[$i]}" --duration 4 --resolution 720p --aspect_ratio 16:9 --generate_audio false)
if [ "$mode" = cost ]; then higgsfield generate cost "${ARGS[@]}"; else higgsfield generate create "${ARGS[@]}" --wait --wait-timeout 20m --json; fi
