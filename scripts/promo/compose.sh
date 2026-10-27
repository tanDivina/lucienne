#!/bin/bash
# Assemble the merged Lucienne demo: real WhatsApp footage + web chat smile +
# Gmail report + the other session's silent cards, all narrated in the garden voice.
# Output: ~/Desktop/Lucienne_Video/lucienne_demo_v2.mp4
set -e
V=~/Projects/lucienne/video
M=$V/merge
A=$M/audio
CARDS=~/Desktop/Lucienne_Video/promo_work/cards
MASK=$M/phone_mask.png
TAKE=$V/whatsapp-demo-take2.mp4
WEB=$V/webchat-take1.mp4
MAIL=$V/email-take1.mp4
SEG=$M/seg
BG=0xf3efe1
mkdir -p "$SEG"

enc="-c:v libx264 -crf 18 -pix_fmt yuv420p -r 30 -c:a aac -ar 44100 -ac 2"

# card <out> <card.mp4> <dur> <voice.mp3> [voice_delay_s]
card() {
  local out=$1 src=$2 dur=$3 vo=$4 delay=${5:-0.4}
  ffmpeg -y -i "$CARDS/$src" -i "$A/$vo" -filter_complex \
    "[0:v]trim=0:$dur,setpts=PTS-STARTPTS[v];[1:a]adelay=${delay}s:all=1,apad[a]" \
    -map "[v]" -map "[a]" -t "$dur" $enc "$SEG/$out" 2>/dev/null
  echo "✓ $out"
}

# phone <out> <start> <end> <speed> <voice.mp3|-> [keep_audio]
phone() {
  local out=$1 ss=$2 to=$3 sp=$4 vo=$5 keep=${6:-no}
  local af vmap
  local vf="[0:v]trim=${ss}:${to},setpts=(PTS-STARTPTS)/${sp},scale=441:980[ph];[ph][1:v]alphamerge[phr];[2:v][phr]overlay=740:50[v]"
  if [ "$keep" = "yes" ]; then
    af="[0:a]atrim=${ss}:${to},asetpts=PTS-STARTPTS,atempo=${sp}[orig]"
    if [ "$vo" != "-" ]; then af="$af;[3:a]adelay=0.2s:all=1[voz];[orig][voz]amix=inputs=2:duration=first:dropout_transition=0.5:normalize=0[a]"
    else af="$af;[orig]anull[a]"; fi
  else
    if [ "$vo" != "-" ]; then af="[3:a]adelay=0.3s:all=1,apad[a]"
    else af="anullsrc=r=44100:cl=stereo[a]"; fi
  fi
  local voin=()
  [ "$vo" != "-" ] && voin=(-i "$A/$vo")
  local dur=$(python3 -c "print(($to-$ss)/$sp)")
  ffmpeg -y -i "$TAKE" -i "$MASK" -f lavfi -i "color=c=$BG:s=1920x1080:r=30" "${voin[@]}" \
    -filter_complex "$vf;$af" -map "[v]" -map "[a]" -t "$dur" $enc "$SEG/$out" 2>/dev/null
  echo "✓ $out"
}

# 01-03 opening cards
card 01_hook.mp4 hook.mp4 11.2 n_hook.mp3
card 02_hook2.mp4 hook2.mp4 5.2 n_hook2.mp3
card 03_meet.mp4 meet.mp4 4.0 n_meet.mp3 0.6

# 04 send the URL + reply arrives (sped waits), n_wa1 over it
phone 04_send.mp4 22.0 44.0 1.3 n_wa1.mp3
# 05 voice note arrives
phone 05_reply.mp4 52.0 62.0 1.15 -
# 06 voice note PLAYS, real audio kept, tiny intro line first
phone 06_vn1.mp4 100.5 123.0 1.0 n_voice.mp3 yes
# 07 speed check: type + send + CWV reply, 53% narration
phone 07_speed.mp4 158.5 188.5 1.5 n_speed.mp3

# 08 web chat beat: normal speed typing+glow, slow-mo on the smile
ffmpeg -y -i "$WEB" -i "$A/n_web.mp3" -filter_complex \
  "[0:v]trim=3:14.8,setpts=(PTS-STARTPTS)/1.25[w1];[0:v]trim=14.8:18.4,setpts=(PTS-STARTPTS)/0.55[w2];[w1][w2]concat=n=2:v=1:a=0,scale=1920:1200,crop=1920:1080:0:40[v];[1:a]adelay=0.4s:all=1,apad[a]" \
  -map "[v]" -map "[a]" -t 16.0 $enc "$SEG/08_web.mp4" 2>/dev/null
echo "✓ 08_web.mp4"

# 09 email ask on WhatsApp ("Done - report sent"), n_email starts here
phone 09_emailwa.mp4 756.5 768.0 1.15 n_email.mp3
# 10 Gmail scroll, sped up, narration tail finishes over it
ffmpeg -y -i "$MAIL" -f lavfi -i "color=c=$BG:s=1920x1080:r=30" -i "$MASK" -filter_complex \
  "[0:v]trim=18:58,setpts=(PTS-STARTPTS)/4,scale=441:980[ph];[ph][2:v]alphamerge[phr];[1:v][phr]overlay=740:50[v];anullsrc=r=44100:cl=stereo[a]" \
  -map "[v]" -map "[a]" -t 10.0 $enc "$SEG/10_gmail.mp4" 2>/dev/null
echo "✓ 10_gmail.mp4"

# 11-14 closing cards
card 11_hub.mp4 hub.mp4 10.5 n_hub.mp3
card 12_arch.mp4 arch.mp4 19.0 n_arch.mp3
card 13_biz.mp4 biz.mp4 12.0 n_biz_fallback.mp3
card 14_end.mp4 end.mp4 6.0 n_close.mp3

# concat
ls "$SEG"/*.mp4 | sed "s/^/file '/;s/$/'/" > "$SEG/list.txt"
ffmpeg -y -f concat -safe 0 -i "$SEG/list.txt" -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -ar 44100 \
  ~/Desktop/Lucienne_Video/lucienne_demo_v2.mp4 2>/dev/null
echo "DONE: ~/Desktop/Lucienne_Video/lucienne_demo_v2.mp4"
ffprobe -v error -show_entries format=duration -of csv=p=0 ~/Desktop/Lucienne_Video/lucienne_demo_v2.mp4
