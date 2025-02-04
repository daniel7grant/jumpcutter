from contextlib import closing
from PIL import Image
import subprocess
from audiotsm import phasevocoder
from audiotsm.io.wav import WavReader, WavWriter
from scipy.io import wavfile
import numpy as np
import re
import math
from shutil import copyfile, rmtree
import os
import glob
import argparse
from pytube import YouTube

def downloadFile(url):
    name = YouTube(url).streams.first().download()
    newname = name.replace(' ','_')
    os.rename(name,newname)
    return newname

def getMaxVolume(s):
    maxv = float(np.max(s))
    minv = float(np.min(s))
    return max(maxv,-minv)

def copyFrame(inputFrame,outputFrame):
    src = TEMP_FOLDER+"/frame{:06d}".format(inputFrame+1)+".jpg"
    dst = TEMP_FOLDER+"/newFrame{:06d}".format(outputFrame+1)+".jpg"
    if not os.path.isfile(src):
        return False
    copyfile(src, dst)
    if outputFrame%20 == 19:
        print(str(outputFrame+1)+" time-altered frames saved.")
    return True

def inputToXmlFilename(filename):
    dotIndex = filename.rfind(".")
    return filename[:dotIndex]+".xml"

def appendIdx(filename, i):
    base, ext = filename.rsplit('.', 1)
    return base + "_" + str(i) + "." + ext

def createPath(s):
    if not os.path.exists(s):
        try:  
            os.mkdir(s)
        except OSError:
            pass

def deleteNewImages(s):
    try:
        fileList = glob.glob(s + '/newFrame*.jpg')
        for filePath in fileList:
            os.remove(filePath)
    except OSError:
        print ("Deletion of the directory %s failed" % s)
        print(OSError)
            

def deletePath(s): # Dangerous! Watch out!
    try:  
        rmtree(s,ignore_errors=False)
    except OSError:  
        print ("Deletion of the directory %s failed" % s)
        print(OSError)


def addVideoClip(path, name, start, end, duration, frameRate):
    return f'''
<clipitem id="{name} 0">
    <name>{name}</name>
    <duration>{duration}</duration>
    <rate>
        <timebase>{frameRate}</timebase>
        <ntsc>FALSE</ntsc>
    </rate>
    <start>{start}</start>
    <end>{end}</end>
    <enabled>TRUE</enabled>
    <in>0</in>
    <out>{duration}</out>
    <file id="{name} 2">
        <duration>{duration}</duration>
        <rate>
            <timebase>{frameRate}</timebase>
            <ntsc>FALSE</ntsc>
        </rate>
        <name>{name}</name>
        <pathurl>file://{os.path.join(path, name)}</pathurl>
        <timecode>
            <string>00:00:00:00</string>
            <displayformat>NDF</displayformat>
            <rate>
                <timebase>{frameRate}</timebase>
                <ntsc>FALSE</ntsc>
            </rate>
        </timecode>
        <media>
            <video>
                <duration>{duration}</duration>
                <samplecharacteristics>
                    <width>1920</width>
                    <height>1080</height>
                </samplecharacteristics>
            </video>
            <audio>
                <channelcount>2</channelcount>
            </audio>
        </media>
    </file>
    <compositemode>normal</compositemode>
</clipitem>
'''


def addAudioClip(path, name, start, end, duration, frameRate):
    return f'''
<clipitem id="{name} 0">
    <name>{name}</name>
    <duration>{duration}</duration>
    <rate>
        <timebase>{frameRate}</timebase>
        <ntsc>FALSE</ntsc>
    </rate>
    <start>{start}</start>
    <end>{end}</end>
    <enabled>TRUE</enabled>
    <in>0</in>
    <out>{duration}</out>
    <file id="{name} 1">
        <duration>{duration}</duration>
        <rate>
            <timebase>{frameRate}</timebase>
            <ntsc>FALSE</ntsc>
        </rate>
        <name>{name}</name>
        <pathurl>file://{os.path.join(path, name)}</pathurl>
        <media>
            <audio>
                <channelcount>2</channelcount>
            </audio>
        </media>
    </file>
    <sourcetrack>
        <mediatype>audio</mediatype>
        <trackindex>1</trackindex>
    </sourcetrack>
    <comments/>
</clipitem>
'''

def createXml(videoClips, audioClips, duration, frameRate):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="5">
    <sequence>
        <name>Timeline 1 (Resolve)</name>
        <duration>{duration}</duration>
        <rate>
            <timebase>{frameRate}</timebase>
            <ntsc>FALSE</ntsc>
        </rate>
        <in>-1</in>
        <out>-1</out>
        <timecode>
            <string>01:00:00:00</string>
            <frame>108000</frame>
            <displayformat>NDF</displayformat>
            <rate>
                <timebase>{frameRate}</timebase>
                <ntsc>FALSE</ntsc>
            </rate>
        </timecode>
        <media>
            <video>
                <track>
                    {" ".join(videoClips)}
                    <enabled>TRUE</enabled>
                    <locked>FALSE</locked>
                </track>
                <format>
                    <samplecharacteristics>
                        <width>1920</width>
                        <height>1080</height>
                        <pixelaspectratio>square</pixelaspectratio>
                        <rate>
                            <timebase>{frameRate}</timebase>
                            <ntsc>FALSE</ntsc>
                        </rate>
                        <codec>
                            <appspecificdata>
                                <appname>Final Cut Pro</appname>
                                <appmanufacturer>Apple Inc.</appmanufacturer>
                                <data>
                                    <qtcodec/>
                                </data>
                            </appspecificdata>
                        </codec>
                    </samplecharacteristics>
                </format>
            </video>
            <audio>
                <track>
                    {" ".join(audioClips)}
                    <enabled>TRUE</enabled>
                    <locked>FALSE</locked>
                </track>
            </audio>
        </media>
    </sequence>
</xmeml>
'''


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



frameRate = args.frame_rate
SAMPLE_RATE = args.sample_rate
SILENT_THRESHOLD = args.silent_threshold
FRAME_SPREADAGE = args.frame_margin
NEW_SPEED = [args.silent_speed, args.sounded_speed]
if args.url != None:
    INPUT_FILE = downloadFile(args.url)
else:
    INPUT_FILE = args.input_file
URL = args.url
FRAME_QUALITY = args.frame_quality

assert INPUT_FILE != None , "why u put no input file, that dum"
    
if len(args.output_file) >= 1:
    OUTPUT_FILE = args.output_file
else:
    OUTPUT_FILE = INPUT_FILE
    
if len(args.output_path) >= 1:
    OUTPUT_PATH = os.path.abspath(args.output_path)
else:
    OUTPUT_PATH = os.getcwd()

if len(args.xml_file) >= 1:
    XML_FILE = os.path.join(OUTPUT_PATH, args.xml_file)
else:
    XML_FILE = os.path.join(OUTPUT_PATH, inputToXmlFilename(INPUT_FILE))

TEMP_FOLDER = "TEMP"
AUDIO_FADE_ENVELOPE_SIZE = 400 # smooth out transitiion's audio by quickly fading in/out (arbitrary magic number whatever)
    
createPath(TEMP_FOLDER)

command = "ffmpeg -i "+INPUT_FILE+" -qscale:v "+str(FRAME_QUALITY)+" "+TEMP_FOLDER+"/frame%06d.jpg -hide_banner"
subprocess.call(command, shell=True)

command = "ffmpeg -i "+INPUT_FILE+" -ab 160k -ac 2 -ar "+str(SAMPLE_RATE)+" -vn "+TEMP_FOLDER+"/audio.wav"
subprocess.call(command, shell=True)

command = "ffmpeg -i "+TEMP_FOLDER+"/input.mp4 2>&1"
f = open(TEMP_FOLDER+"/params.txt", "w")
subprocess.call(command, shell=True, stdout=f)



sampleRate, audioData = wavfile.read(TEMP_FOLDER+"/audio.wav")
audioSampleCount = audioData.shape[0]
maxAudioVolume = getMaxVolume(audioData)

f = open(TEMP_FOLDER+"/params.txt", 'r+')
pre_params = f.read()
f.close()
params = pre_params.split('\n')
for line in params:
    m = re.search('Stream #.*Video.* ([0-9]*) fps',line)
    if m is not None:
        frameRate = float(m.group(1))

samplesPerFrame = sampleRate/frameRate

audioFrameCount = int(math.ceil(audioSampleCount/samplesPerFrame))

hasLoudAudio = np.zeros((audioFrameCount))



for i in range(audioFrameCount):
    start = int(i*samplesPerFrame)
    end = min(int((i+1)*samplesPerFrame),audioSampleCount)
    audiochunks = audioData[start:end]
    maxchunksVolume = float(getMaxVolume(audiochunks))/maxAudioVolume
    if maxchunksVolume >= SILENT_THRESHOLD:
        hasLoudAudio[i] = 1

chunks = [[0,0,0]]
shouldIncludeFrame = np.zeros((audioFrameCount))
for i in range(audioFrameCount):
    start = int(max(0,i-FRAME_SPREADAGE))
    end = int(min(audioFrameCount,i+1+FRAME_SPREADAGE))
    shouldIncludeFrame[i] = np.max(hasLoudAudio[start:end])
    if (i >= 1 and shouldIncludeFrame[i] != shouldIncludeFrame[i-1]): # Did we flip?
        chunks.append([chunks[-1][1],i,shouldIncludeFrame[i-1]])

chunks.append([chunks[-1][1],audioFrameCount,shouldIncludeFrame[i-1]])
chunks = chunks[1:]

outputAudioData = np.zeros((0,audioData.shape[1]))
outputPointer = 0

path = os.getcwd()
i = 0
frameIndex = 0
videoClips = []
audioClips = []

lastExistingFrame = None
for chunk in chunks:
    audioChunk = audioData[int(chunk[0]*samplesPerFrame):int(chunk[1]*samplesPerFrame)]
    
    sFile = TEMP_FOLDER+"/tempStart.wav"
    eFile = TEMP_FOLDER+"/tempEnd.wav"
    wavfile.write(sFile,SAMPLE_RATE,audioChunk)
    with WavReader(sFile) as reader:
        with WavWriter(eFile, reader.channels, reader.samplerate) as writer:
            tsm = phasevocoder(reader.channels, speed=NEW_SPEED[int(chunk[2])])
            tsm.run(reader, writer)
    _, alteredAudioData = wavfile.read(eFile)
    leng = alteredAudioData.shape[0]
    endPointer = outputPointer+leng
    outputAudioData = np.concatenate((outputAudioData,alteredAudioData/maxAudioVolume))

    #outputAudioData[outputPointer:endPointer] = alteredAudioData/maxAudioVolume

    # smooth out transitiion's audio by quickly fading in/out
    
    if leng < AUDIO_FADE_ENVELOPE_SIZE:
        outputAudioData[outputPointer:endPointer] = 0 # audio is less than 0.01 sec, let's just remove it.
    else:
        premask = np.arange(AUDIO_FADE_ENVELOPE_SIZE)/AUDIO_FADE_ENVELOPE_SIZE
        mask = np.repeat(premask[:, np.newaxis],2,axis=1) # make the fade-envelope mask stereo
        outputAudioData[outputPointer:outputPointer+AUDIO_FADE_ENVELOPE_SIZE] *= mask
        outputAudioData[endPointer-AUDIO_FADE_ENVELOPE_SIZE:endPointer] *= 1-mask

    startOutputFrame = int(math.ceil(outputPointer/samplesPerFrame))
    endOutputFrame = int(math.ceil(endPointer/samplesPerFrame))
    for outputFrame in range(startOutputFrame, endOutputFrame):
        inputFrame = int(chunk[0]+NEW_SPEED[int(chunk[2])]*(outputFrame-startOutputFrame))
        didItWork = copyFrame(inputFrame,outputFrame)
        if didItWork:
            lastExistingFrame = inputFrame
        else:
            copyFrame(lastExistingFrame,outputFrame)

    duration = endOutputFrame - startOutputFrame

    if NEW_SPEED[int(chunk[2])] < 1.1:
        outputPointer = endPointer
        wavfile.write(TEMP_FOLDER+"/audioNew.wav",SAMPLE_RATE,outputAudioData)
        
        i += 1
        filename = appendIdx(OUTPUT_FILE, i)
        outputFile = os.path.join(OUTPUT_PATH, filename)
        extraFlags = "-c:v dnxhd -profile:v dnxhr_hq -pix_fmt yuv422p -c:a pcm_s16le" if OUTPUT_FILE.endswith('.mov') else ""
        command = "ffmpeg -y -framerate "+str(frameRate)+" -i "+TEMP_FOLDER+"/newFrame%06d.jpg -i "+TEMP_FOLDER+"/audioNew.wav -strict -2 " + extraFlags + " " + outputFile
        subprocess.call(command, shell=True)

        videoClips.append(addVideoClip(OUTPUT_PATH, filename, frameIndex, frameIndex + duration, duration, frameRate))
        audioClips.append(addAudioClip(OUTPUT_PATH, filename, frameIndex, frameIndex + duration, duration, frameRate))

    frameIndex += duration

    outputPointer = 0
    outputAudioData = np.zeros((0,audioData.shape[1]))
        
    deleteNewImages(TEMP_FOLDER)

with open(XML_FILE, "w") as xml_file:
    xml_file.write(createXml(videoClips, audioClips, frameIndex, frameRate))

deletePath(TEMP_FOLDER)

