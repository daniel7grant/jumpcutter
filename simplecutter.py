import argparse
import json
import numpy as np
import subprocess
from scipy.io import wavfile


def getMaxVolume(s):
    maxv = float(np.max(s))
    minv = float(np.min(s))
    return max(maxv,-minv)


parser = argparse.ArgumentParser(description='Modifies a video file to play at different speeds when there is sound vs. silence.')
parser.add_argument('--input_file', type=str,  help='the video file you want modified')
parser.add_argument('--url', type=str, help='A youtube url to download and process')
parser.add_argument('--output_file', type=str, default="", help="the output file. (optional. if not included, it'll just be the input file name)")
parser.add_argument('--output_path', type=str, default="", help="the location where it should put the output files. (by default: local directory)")
parser.add_argument('--xml_file', type=str, default="", help="the XML timeline output. (default: the input file's name + .xml)")
parser.add_argument('--silent_threshold', type=float, default=0.03, help="the volume amount that frames' audio needs to surpass to be consider \"sounded\". It ranges from 0 (silence) to 1 (max volume)")
parser.add_argument('--sounded_speed', type=float, default=1.00, help="the speed that sounded (spoken) frames should be played at. Typically 1.")
parser.add_argument('--silent_speed', type=float, default=5.00, help="the speed that silent frames should be played at. 999999 for jumpcutting.")
parser.add_argument('--frame_margin', type=float, default=1, help="some silent frames adjacent to sounded frames are included to provide context. How many frames on either the side of speech should be included? That's this variable.")
parser.add_argument('--sample_rate', type=float, default=44100, help="sample rate of the input and output videos")
parser.add_argument('--frame_rate', type=float, default=30, help="frame rate of the input and output videos. optional... I try to find it out myself, but it doesn't always work.")
parser.add_argument('--frame_quality', type=int, default=3, help="quality of frames to be extracted from input video. 1 is highest, 31 is lowest, 3 is the default.")

args = parser.parse_args()

SAMPLE_RATE = args.sample_rate or 30
FRAME_RATE = args.frame_rate or 30

INPUT_FILE = args.input_file
assert INPUT_FILE != None , "why u put no input file, that dum"
    
if len(args.output_file) >= 1:
    OUTPUT_FILE = args.output_file
else:
    OUTPUT_FILE = INPUT_FILE

command = "ffmpeg -y -i "+INPUT_FILE+" -ab 160k -ac 2 -ar "+str(SAMPLE_RATE)+" -vn audio.wav"
subprocess.call(command, shell=True)

sampleRate, audioData = wavfile.read("audio.wav")
audioSampleCount = audioData.shape[0]
maxAudioVolume = getMaxVolume(audioData)

groupedAudioData = np.array_split(audioData, int(sampleRate / FRAME_RATE))
avgAudioData = list(map(getMaxVolume, groupedAudioData))
print(avgAudioData)