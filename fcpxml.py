from os import path, sep


class FcpXmlBuilder:
    def __init__(self, sourceFile, dimensions, frameRate, duration):
        self.name = path.basename(sourceFile)
        self.sourceFile = sourceFile.replace(sep, '/')
        if not self.sourceFile.startswith('/'):
            self.sourceFile = f"/{self.sourceFile}"
        (width, height) = dimensions
        self.width = width
        self.height = height
        self.frameRate = frameRate
        self.duration = duration
        self.fileIndex = 0 # for some reason the file index has to be different than clip index
        self.index = 1
        self.frameIndex = 0
        self.videoClips = []
        self.audioClips = []

    def addClip(self, start, end):
        self.addVideoClip(start, end)
        self.addAudioClip(start, end)
        self.frameIndex += end - start

    def addVideoClip(self, start, end):
        self.videoClips.append(
            f'''
                    <clipitem id="{self.name} {self.index}">
                        <name>{self.name}</name>
                        <duration>{self.duration}</duration>
                        <rate>
                            <timebase>{self.duration}</timebase>
                            <ntsc>FALSE</ntsc>
                        </rate>
                        <start>{self.frameIndex}</start>
                        <end>{self.frameIndex + (end - start)}</end>
                        <enabled>TRUE</enabled>
                        <in>{start}</in>
                        <out>{end}</out>
                        <file id="{self.name} {self.fileIndex}">
                            <duration>{self.duration}</duration>
                            <rate>
                                <timebase>{self.frameRate}</timebase>
                                <ntsc>FALSE</ntsc>
                            </rate>
                            <name>{self.name}</name>
                            <pathurl>file://{self.sourceFile}</pathurl>
                            <timecode>
                                <string>00:00:00:00</string>
                                <displayformat>NDF</displayformat>
                                <rate>
                                    <timebase>{self.frameRate}</timebase>
                                    <ntsc>FALSE</ntsc>
                                </rate>
                            </timecode>
                            <media>
                                <video>
                                    <duration>{self.duration}</duration>
                                    <samplecharacteristics>
                                        <width>{self.width}</width>
                                        <height>{self.height}</height>
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
        )
        self.index += 1

    def addAudioClip(self, start, end):
        self.audioClips.append(
            f'''
                    <clipitem id="{self.name} {self.index}">
                        <name>{self.name}</name>
                        <duration>{self.duration}</duration>
                        <rate>
                            <timebase>{self.frameRate}</timebase>
                            <ntsc>FALSE</ntsc>
                        </rate>
                        <start>{self.frameIndex}</start>
                        <end>{self.frameIndex + (end - start)}</end>
                        <enabled>TRUE</enabled>
                        <in>{start}</in>
                        <out>{end}</out>
                        <file id="{self.name} {self.fileIndex}">
                            <duration>{self.duration}</duration>
                            <rate>
                                <timebase>{self.frameRate}</timebase>
                                <ntsc>FALSE</ntsc>
                            </rate>
                            <name>{self.name}</name>
                            <pathurl>file://{self.sourceFile}</pathurl>
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
        )
        self.index += 1

    def dump(self):
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="5">
    <sequence>
        <name>Timeline {self.name}</name>
        <duration>{self.duration}</duration>
        <rate>
            <timebase>{self.frameRate}</timebase>
            <ntsc>FALSE</ntsc>
        </rate>
        <in>-1</in>
        <out>-1</out>
        <timecode>
            <string>01:00:00:00</string>
            <frame>108000</frame>
            <displayformat>NDF</displayformat>
            <rate>
                <timebase>{self.frameRate}</timebase>
                <ntsc>FALSE</ntsc>
            </rate>
        </timecode>
        <media>
            <video>
                <track>
                    {" ".join(self.videoClips)}
                    <enabled>TRUE</enabled>
                    <locked>FALSE</locked>
                </track>
                <format>
                    <samplecharacteristics>
                        <width>{self.width}</width>
                        <height>{self.height}</height>
                        <pixelaspectratio>square</pixelaspectratio>
                        <rate>
                            <timebase>{self.frameRate}</timebase>
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
                    {" ".join(self.audioClips)}
                    <enabled>TRUE</enabled>
                    <locked>FALSE</locked>
                </track>
            </audio>
        </media>
    </sequence>
</xmeml>
'''        

