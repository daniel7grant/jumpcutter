import argparse
import json
import numpy as np
import re
import subprocess
from fcpxml import FcpXmlBuilder
from functools import reduce
from os import path
from scipy.io import wavfile


def getMaxVolume(s):
    maxv = float(np.max(s))
    minv = float(np.min(s))
    return max(maxv, -minv)


def groupTuples(xs, n):
    return list(map(
        lambda i: xs[max(0, i - n): min(i + n, len(xs))],
        range(len(xs))
    ))


def inputToXmlFilename(filename):
    dotIndex = filename.rfind(".")
    return filename[:dotIndex]+".xml"


# Handle parameters and setup values
parser = argparse.ArgumentParser(
    description='Modifies a video file to play at different speeds when there is sound vs. silence.')
parser.add_argument('--input_file', type=str,
                    help='the video file you want modified')
parser.add_argument('--xml_file', type=str, default="",
                    help="the XML timeline output. (default: the input file's name + .xml)")
parser.add_argument('--silent_threshold', type=float, default=0.03,
                    help="the volume amount that frames' audio needs to surpass to be consider \"sounded\". It ranges from 0 (silence) to 1 (max volume)")
parser.add_argument('--frame_margin', type=int, default=1,
                    help="some silent frames adjacent to sounded frames are included to provide context. How many frames on either the side of speech should be included? That's this variable.")
parser.add_argument('--sample_rate', type=float, default=44100,
                    help="sample rate of the input and output videos")
parser.add_argument('--frame_rate', type=float, default=30,
                    help="frame rate of the input and output videos. optional... I try to find it out myself, but it doesn't always work.")

args = parser.parse_args()

# Setup variables
SILENT_THRESHOLD = args.silent_threshold
SAMPLE_RATE = args.sample_rate
FRAME_RATE = args.frame_rate
FRAME_MARGIN = args.frame_margin
DIMENSIONS = (1920, 1080)  # probably

INPUT_FILE = path.abspath(args.input_file)
assert INPUT_FILE != None, "you have to add an input file"

if len(args.xml_file) >= 1:
    XML_FILE = path.abspath(args.xml_file)
else:
    XML_FILE = inputToXmlFilename(INPUT_FILE)

# Get video metadata
# metadata = subprocess.run(["ffprobe", INPUT_FILE], capture_output=True).stderr.decode("utf-8")
# frameRateMatches = re.search(r'([0-9]+) fps', metadata)
# if frameRateMatches is not None:
#     FRAME_RATE = int(frameRateMatches.group(1))

# sampleRateMatches = re.search(r'([0-9]+) Hz', metadata)
# if sampleRateMatches is not None:
#     SAMPLE_RATE = int(sampleRateMatches.group(1))

# dimensionMatches = re.search(r'([0-9]+)x([0-9]+)', metadata)
# if dimensionMatches is not None:
#     DIMENSIONS = (int(dimensionMatches.group(1)), int(dimensionMatches.group(2)))

frames = subprocess.run([
    "ffprobe",
    "-v", "error",
    "-select_streams", "v:0",
    "-count_packets",
    "-show_entries", "stream=nb_read_packets",
    "-of", "csv=p=0",
    INPUT_FILE
], capture_output=True).stdout.decode("utf-8")
frames = re.sub("[^0-9]", "", frames)
DURATION = int(frames)

# Generate wav file to calculate peaks
subprocess.run([
    "ffmpeg",
    "-y",
    "-i", INPUT_FILE,
    "-ab", "160k",
    "-ac", "2",
    "-ar", f"{SAMPLE_RATE}",
    "-vn", "audio.wav",
], capture_output=True)
sampleRate, audioData = wavfile.read("audio.wav")
maxAudioVolume = getMaxVolume(audioData)

# Generate list of bool values for silent (False) and loud (True) parts
seconds = int(audioData.shape[0] / sampleRate * FRAME_RATE)
groupedAudioData = np.array_split(audioData, seconds)
avgAudioData = map(getMaxVolume, groupedAudioData)
loudAudioData = list(map(
    lambda x: x > maxAudioVolume * SILENT_THRESHOLD,
    avgAudioData
))
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
    ends.append(len(fuzzyLoudAudioData) - 1)

# Create XML clips for every start and end
fcpxml = FcpXmlBuilder(INPUT_FILE, DIMENSIONS, FRAME_RATE, DURATION)
for (start, end) in zip(starts, ends):
    fcpxml.addClip(start, end)

# Write output to XML file
with open(XML_FILE, "w") as xml_file:
    xml_file.write(fcpxml.dump())
