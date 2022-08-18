import argparse
import json
import numpy as np
import subprocess
from functools import reduce
from scipy.io import wavfile


def getMaxVolume(s):
    maxv = float(np.max(s))
    minv = float(np.min(s))
    return max(maxv,-minv)

def groupTuples(xs, n):
    return list(map(
        lambda i: xs[i : min(i + n, len(xs))],
        range(len(xs))
    ))


# Handle parameters and setup values
parser = argparse.ArgumentParser(description='Modifies a video file to play at different speeds when there is sound vs. silence.')
parser.add_argument('--input_file', type=str,  help='the video file you want modified')
parser.add_argument('--url', type=str, help='A youtube url to download and process')
parser.add_argument('--output_file', type=str, default="", help="the output file. (optional. if not included, it'll just be the input file name)")
parser.add_argument('--output_path', type=str, default="", help="the location where it should put the output files. (by default: local directory)")
parser.add_argument('--xml_file', type=str, default="", help="the XML timeline output. (default: the input file's name + .xml)")
parser.add_argument('--silent_threshold', type=float, default=0.03, help="the volume amount that frames' audio needs to surpass to be consider \"sounded\". It ranges from 0 (silence) to 1 (max volume)")
parser.add_argument('--frame_margin', type=int, default=1, help="some silent frames adjacent to sounded frames are included to provide context. How many frames on either the side of speech should be included? That's this variable.")
parser.add_argument('--sample_rate', type=float, default=44100, help="sample rate of the input and output videos")
parser.add_argument('--frame_rate', type=float, default=30, help="frame rate of the input and output videos. optional... I try to find it out myself, but it doesn't always work.")
parser.add_argument('--frame_quality', type=int, default=3, help="quality of frames to be extracted from input video. 1 is highest, 31 is lowest, 3 is the default.")

args = parser.parse_args()

SILENT_THRESHOLD = args.silent_threshold
SAMPLE_RATE = args.sample_rate
FRAME_RATE = args.frame_rate
FRAME_MARGIN = args.frame_margin

INPUT_FILE = args.input_file
assert INPUT_FILE != None , "you have to add an input file"
    
if len(args.output_file) >= 1:
    OUTPUT_FILE = args.output_file
else:
    OUTPUT_FILE = INPUT_FILE

# Generate wav file to calculate peaks
command = "ffmpeg -y -i "+INPUT_FILE+" -ab 160k -ac 2 -ar "+str(SAMPLE_RATE)+" -vn audio.wav"
subprocess.call(command, shell=True)
sampleRate, audioData = wavfile.read("audio.wav")
maxAudioVolume = getMaxVolume(audioData)

# Generate list of bool values for silent (False) and loud (True) parts
groupedAudioData = np.array_split(audioData, int(sampleRate / FRAME_RATE))
avgAudioData = map(getMaxVolume, groupedAudioData)
loudAudioData = list(map(lambda x: x > maxAudioVolume * SILENT_THRESHOLD, avgAudioData))
fuzzyLoudAudioData = list(map(any, groupTuples(loudAudioData, FRAME_MARGIN)))

# Find the start and end of loud clips
starts = []
ends = []
for index, group in enumerate(groupTuples(fuzzyLoudAudioData, 2)):
    if len(group) == 2:
        [before, after] = group
        if before == False and after == True:  # start of loud part
            starts.append(index)
        if before == True and after == False:  # end of loud part
            ends.append(index)

# Handle where the beginning is loud
if fuzzyLoudAudioData[0]:
    starts.insert(0, 0)

# Handle when the end is loud
if fuzzyLoudAudioData[-1]:
    ends.append(len(fuzzyLoudAudioData))

# Print starts and ends
print(list(zip(starts, ends)))