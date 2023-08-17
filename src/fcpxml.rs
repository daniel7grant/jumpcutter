use std::{fmt::Display, path::Path};

pub struct FcpClip(usize, usize);

impl FcpClip {
    fn new(start: usize, end: usize) -> Self {
        FcpClip(start, end)
    }

    fn to_audio_string(&self, fcp: &Fcp, index: usize) -> String {
        let Fcp {
            source_file,
            name,
            frame_rate,
            duration,
            ..
        } = fcp;

        let FcpClip(start, end) = self;
        let frame_start = end - start;
        let frame_end = frame_start + (end - start);

        format!(
            r#"                    <clipitem id="{name} {index}">
                        <name>{name}</name>
                        <duration>{duration}</duration>
                        <rate>
                            <timebase>{frame_rate}</timebase>
                            <ntsc>FALSE</ntsc>
                        </rate>
                        <start>{frame_start}</start>
                        <end>{frame_end}</end>
                        <enabled>TRUE</enabled>
                        <in>{start}</in>
                        <out>{end}</out>
                        <file id="{name} {index}">
                            <duration>{duration}</duration>
                            <rate>
                                <timebase>{frame_rate}</timebase>
                                <ntsc>FALSE</ntsc>
                            </rate>
                            <name>{name}</name>
                            <pathurl>file://{source_file}</pathurl>
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
                    </clipitem>"#
        )
    }

    fn to_video_string(&self, fcp: &Fcp, index: usize) -> String {
        let Fcp {
            source_file,
            name,
            dimensions: (width, height),
            frame_rate,
            duration,
            ..
        } = fcp;

        let FcpClip(start, end) = self;
        let frame_start = end - start;
        let frame_end = frame_start + (end - start);

        format!(
            r#"                    <clipitem id="{name} {index}">
                        <name>{name}</name>
                        <duration>{duration}</duration>
                        <rate>
                            <timebase>{duration}</timebase>
                            <ntsc>FALSE</ntsc>
                        </rate>
                        <start>{frame_start}</start>
                        <end>{frame_end}</end>
                        <enabled>TRUE</enabled>
                        <in>{start}</in>
                        <out>{end}</out>
                        <file id="{name} {index}">
                            <duration>{duration}</duration>
                            <rate>
                                <timebase>{frame_rate}</timebase>
                                <ntsc>FALSE</ntsc>
                            </rate>
                            <name>{name}</name>
                            <pathurl>file://{source_file}</pathurl>
                            <timecode>
                                <string>00:00:00:00</string>
                                <displayformat>NDF</displayformat>
                                <rate>
                                    <timebase>{frame_rate}</timebase>
                                    <ntsc>FALSE</ntsc>
                                </rate>
                            </timecode>
                            <media>
                                <video>
                                    <duration>{duration}</duration>
                                    <samplecharacteristics>
                                        <width>{width}</width>
                                        <height>{height}</height>
                                    </samplecharacteristics>
                                </video>
                                <audio>
                                    <channelcount>2</channelcount>
                                </audio>
                            </media>
                        </file>index
                        <compositemode>normal</compositemode>
                    </clipitem>"#
        )
    }
}

pub struct Fcp {
    source_file: String,
    name: String,
    dimensions: (u64, u64),
    frame_rate: u64,
    duration: u64,
    clips: Vec<FcpClip>,
}

impl Fcp {
    pub fn new(
        source_file: String,
        dimensions: (u64, u64),
        frame_rate: u64,
        duration: u64,
        clips: Vec<(usize, usize)>,
    ) -> Self {
        let s = source_file.clone();
        let f = Path::new(&s);
        Fcp {
            source_file,
            name: f
                .file_name()
                .map(|s| s.to_string_lossy().to_string())
                .unwrap_or("".to_string()),
            dimensions,
            frame_rate,
            duration,
            clips: clips
                .into_iter()
                .map(|(s, e)| FcpClip::new(s, e))
                .collect::<Vec<_>>(),
        }
    }
}

impl Display for Fcp {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let Fcp {
            source_file: _,
            name,
            dimensions: (width, height),
            frame_rate,
            duration,
            clips,
        } = self;

        let audio_clips = clips
            .iter()
            .enumerate()
            .map(|(i, clip)| clip.to_audio_string(self, i))
            .collect::<Vec<_>>()
            .join("\n");
        let video_clips = clips
            .iter()
            .enumerate()
            .map(|(i, clip)| clip.to_video_string(self, i))
            .collect::<Vec<_>>()
            .join("\n");

        write!(
            f,
            r#"<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="5">
    <sequence>
        <name>Timeline {name}</name>
        <duration>{duration}</duration>
        <rate>
            <timebase>{frame_rate}</timebase>
            <ntsc>FALSE</ntsc>
        </rate>
        <in>-1</in>
        <out>-1</out>
        <timecode>
            <string>01:00:00:00</string>
            <frame>108000</frame>
            <displayformat>NDF</displayformat>
            <rate>
                <timebase>{frame_rate}</timebase>
                <ntsc>FALSE</ntsc>
            </rate>
        </timecode>
        <media>
            <video>
                <track>
{video_clips}
                    <enabled>TRUE</enabled>
                    <locked>FALSE</locked>
                </track>
                <format>
                    <samplecharacteristics>
                        <width>{width}</width>
                        <height>{height}</height>
                        <pixelaspectratio>square</pixelaspectratio>
                        <rate>
                            <timebase>{frame_rate}</timebase>
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
{audio_clips}
                    <enabled>TRUE</enabled>
                    <locked>FALSE</locked>
                </track>
            </audio>
        </media>
    </sequence>
</xmeml>"#
        )
    }
}
