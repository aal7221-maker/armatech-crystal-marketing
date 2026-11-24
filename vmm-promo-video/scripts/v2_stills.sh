#!/usr/bin/env bash
# v2 photoreal technical stills (Nano Banana Pro 2k). Usage: v2_stills.sh <1-5> [cost|run]
set -euo pipefail
R=v2/ref
MACHINE="The machine is the exact video measuring machine shown in the reference photos: light-grey rectangular camera head with a red vertical accent band on its side, long black zoom lens tube with a black ring light at the bottom, black vertical column, a black corrugated cable running down the column, rounded black XY stage with a clear glass plate, speckled black granite base. Keep its exact shape and proportions, no extra parts."
LOOK="Photorealistic high-end industrial product photography, shot on a medium-format camera, real materials (brushed and powder-coated metal, polished black granite with speckles, clear glass), soft controlled studio key light with subtle cool rim light, clean modern quality-control metrology room inside a precision manufacturing factory, background softly out of focus, natural shadows, true-to-life color, crisp detail, 16:9 frame. No text, no labels, no logos, no watermark, no screens with text."
SHOT=(x
 "Shot: hero three-quarter view of the complete machine standing on a clean white lab bench, camera at stage height, the whole machine sharp from head to base, factory QC room behind with glass partition and blurred CNC machines."
 "Shot: low close-up tracking angle along the front edge of the rounded black XY stage and its glass plate sitting on the speckled black granite base; a technician's hand in a blue shirt cuff rests on the stage edge, about to slide it; shallow depth of field."
 "Shot: top-down macro looking through the clear glass plate into the polished speckled black granite base, showing the round black bottom-light housing with a dense circular array of small white LEDs (switched off, dark), metal mounting holes around it."
 "Shot: close-up of a technician's hand gently placing a small precision-machined steel threaded shaft onto the glass stage, directly under the black zoom lens and ring light; machine column softly out of focus."
 "Shot: side close-up of the long black zoom lens tube and the black ring light hovering just above a small machined steel part lying on the glass stage, the light-grey camera head with its red accent band at the top of frame; shallow depth of field.")
REFS=(x
 "--image $R/real_58.5.png --image $R/real_55.png --image $R/real_72.png --image ref_fullauto.png"
 "--image $R/real_3.png --image $R/real_9.png --image $R/real_13.png"
 "--image $R/real_16.png"
 "--image $R/real_20.5.png --image $R/real_67.png --image $R/real_75.png"
 "--image $R/real_67.png --image $R/real_72.png --image $R/real_75.png --image $R/real_55.png")
# v2 re-rolls (index 6 = hero redo, 7 = LED redo)
SHOT+=(
 "Shot: hero three-quarter view of the complete machine on a clean light lab bench, camera slightly below stage height, whole machine sharp from top of the head to the levelling feet. Exact layout: a rectangular speckled black granite base block on four levelling feet; on it a rectangular black XY stage whose front and back edges are rounded cylindrical rails, with a clear glass plate set into a granite-topped table and a small silver knob on the right front; a tall black column rising from the rear; a tall light-grey vertical rectangular camera head mounted in front of the column with a red vertical accent band on its side; a black zoom lens hanging down from the head toward the glass; a black corrugated cable from the head down the column. Factory QC room softly blurred behind."
 "Shot: straight top-down macro looking through the clear glass plate into the polished speckled black granite of the stage, centered on a round recessed black bottom-light housing filled with a dense circular array of tiny flat white LED dots (switched off), a few round metal screw holes in the granite around it. No lens, no camera head and nothing else in frame. All surfaces completely plain, no markings, no engravings.")
REFS+=(
 "--image $R/real_full_crop.png --image $R/real_full_crop2.png --image v2/stills/s2_stage.png --image $R/real_9.png"
 "--image $R/real_16.png --image v2/stills/s2_stage.png")
# 8 = full-machine opener (whole unit head to feet, room around it for an orbit)
SHOT+=("Shot: wide establishing hero shot of the COMPLETE machine, entire unit visible from the top of the light-grey camera head down to the levelling feet with generous empty space above and around it, three-quarter front view, camera at stage height, machine centered and occupying about 60 percent of the frame height, standing on a clean light lab bench in a bright modern quality-control room, background softly blurred. Exact layout: rectangular speckled black granite base block on four levelling feet; rectangular black XY stage with rounded cylindrical front and back rails, clear glass plate, small silver knob at the right front; tall black column at the rear; tall light-grey vertical rectangular camera head mounted in front of the column with a red vertical accent band on its SIDE face only; black zoom lens hanging down toward the glass; black corrugated cable from the head down the column.")
REFS+=("--image $R/real_full_crop.png --image $R/real_full_crop2.png --image v2/stills/s_hero_v2.png --image v2/stills/s2_stage.png")
i=$1; mode=${2:-cost}
read -ra IM <<< "${REFS[$i]}"
ARGS=(nano_banana_pro --prompt "${SHOT[$i]} $MACHINE $LOOK" "${IM[@]}" --aspect_ratio 16:9 --resolution 2k)
if [ "$mode" = cost ]; then higgsfield generate cost "${ARGS[@]}"; else higgsfield generate create "${ARGS[@]}" --wait --json; fi
