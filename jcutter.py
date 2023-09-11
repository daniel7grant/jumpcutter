import argparse
from argparse import RawTextHelpFormatter
import json
import xmltodict
from fcpxml.fcpxml import FcpXml, Clip, Track
from typing import Optional

parser = argparse.ArgumentParser(description='''Modifies a timeline file to collapse clips to J-cuts. Slide the audio clips into each other, while truncating the videos:

+-----++-------++-----+          +-----++-----++---+
+  V  ++   V   ++  V  +          +  V  ++  V  ++ V +
+-----++-------++-----+          +-----++-----++---+
+-----++-------++-----+          +-----+     +-----+
+  A  ++   A   ++  A  +    =>    +  A  +     +  A  +
+-----++-------++-----+          +-----+     +-----+
                                      +-------+
                                      +   A   +
                                      +-------+''', formatter_class=RawTextHelpFormatter)
parser.add_argument('--input_file', required=True, type=str, help='the timeline you want modified')
parser.add_argument('--output_file', type=str, help='the timeline containing the J-cuts')
parser.add_argument('--min_frames', type=int, help='the minimum size in frames that should be J-cut (default=10)', default=10)
parser.add_argument('--cut', type=int, help='the number of frames to move the audio back (default=3)', default=3)

args = parser.parse_args()

input_file = args.input_file
output_file = input_file.replace(".xml", "_result.xml")
if args.output_file is not None:
    output_file = args.output_file
min_frames = args.min_frames
cut = args.cut

# Parse clips from XML file
f: Optional[FcpXml] = None
with open(input_file, "r") as infile:
    d = xmltodict.parse(infile.read())
    f = FcpXml.parse(d)

# Pair video and audio clips
clips: list[tuple[Clip, Clip]] = []
for clip in f.video_tracks[0].clips:
    found_audio_tracks = list(filter(lambda c: c.is_linked_to(clip.id), f.audio_tracks[0].clips))

    if len(found_audio_tracks) == 0:
        print(f"WARNING: there is no audio file for clip between {clip.start} and {clip.end}")
        continue

    clips.append((clip, found_audio_tracks[0]))

# Slide the clips one-by-one, to the J-cut position
slide = 0
videoclips1: list[Clip] = []
audioclips1: list[Clip] = []
audioclips2: list[Clip] = []
for i, (video, audio) in enumerate(clips):
    # No J-cut for the first clip and short clips
    if i > 0 and video.end - video.start >= min_frames:
        # The total slide should get bigger
        slide += cut

        # Video should be pushed back, and cut from the beginning
        video.start -= slide - cut
        video.end -= slide
        video.in_param += cut

        # Audio should be pushed back
        audio.start -= slide
        audio.end -= slide

    # Add videos to track and audios to separate tracks
    videoclips1.append(video)
    if i % 2 == 1:
        audioclips1.append(audio)
    else:
        audioclips2.append(audio)

# Update tracks with J-cut timings
f.video_tracks[0].clips = videoclips1
f.audio_tracks[0].clips = audioclips1
if len(f.audio_tracks) == 1:
    track = Track()
    track.enabled = True
    track.locked = False
    f.audio_tracks.append(track)
f.audio_tracks[1].clips = audioclips2

with open(output_file, "w") as outfile:
    d = f.dump()
    outfile.write(xmltodict.unparse(d, pretty=True))

