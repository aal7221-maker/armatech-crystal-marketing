#!/usr/bin/env bash
# Cut v3 source segments to exact 1280x720 @30fps lengths (motion-interpolated, speed-fit).
set -euo pipefail
FB=/c/Users/lunaw/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build/bin
mkdir -p v3/seg
N=v3/src/new15.mp4; O=v3/src/cinema30.mp4
# name  src  in  out  target_seconds
cut() {
  local name=$1 src=$2 a=$3 b=$4 dur=$5
  local f; f=$(awk -v a=$a -v b=$b -v d=$dur 'BEGIN{printf "%.5f", d/(b-a)}')
  "$FB/ffmpeg.exe" -y -v error -ss "$a" -to "$b" -i "$src" -an \
    -vf "setpts=${f}*(PTS-STARTPTS),scale=1280:720:flags=lanczos,minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:vsbmc=1" \
    -frames:v $(awk -v d=$dur 'BEGIN{printf "%d", d*30+0.5}') -c:v libx264 -crf 12 -preset fast "v3/seg/$name.mp4"
  echo "$name ok"
}
cut zfocus  $N 12.58 15.00 3.0  &
cut stage   $N 4.83  6.95  2.0  &
cut knob    $O 7.29  9.00  1.8  &
cut screw   $N 7.21  9.67  2.5  &
cut scale   $O 19.08 21.08 2.0  &
cut led     $N 9.75  11.06 1.5  &
cut bolt    $N 11.12 12.50 1.5  &
wait
