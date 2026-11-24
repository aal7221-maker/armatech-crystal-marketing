#!/usr/bin/env bash
# Cut v5 source segments at 1920x1080 @30fps (lanczos upscale for 720p sources, native for 1080p ones).
set -euo pipefail
FB=/c/Users/lunaw/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build/bin
mkdir -p v5hd/seg
N=v3/src/new15.mp4; O=v3/src/cinema30.mp4; OP=v4/src/opener.mp4
cut() {
  local name=$1 src=$2 a=$3 b=$4 dur=$5
  local f; f=$(awk -v a=$a -v b=$b -v d=$dur 'BEGIN{printf "%.5f", d/(b-a)}')
  "$FB/ffmpeg.exe" -y -v error -ss "$a" -to "$b" -i "$src" -an \
    -vf "setpts=${f}*(PTS-STARTPTS),scale=1920:1080:flags=lanczos,minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:vsbmc=1,unsharp=5:5:0.35:5:5:0" \
    -frames:v $(awk -v d=$dur 'BEGIN{printf "%d", d*30+0.5}') -c:v libx264 -crf 10 -preset fast "v5hd/seg/$name.mp4"
  echo "$name ok"
}
cut opener  $OP 0.00  5.00  5.0 &
cut zfocus  $N 12.58 15.00 3.0  &
cut stage   $N 4.83  6.95  3.5  &
cut knob    $O 7.29  9.00  3.0  &
wait
cut screw   $N 7.21  9.67  3.5  &
cut scale   $O 19.08 21.08 3.5  &
cut led     $N 9.75  11.06 3.0  &
cut bolt    $N 11.12 12.50 3.0  &
wait
