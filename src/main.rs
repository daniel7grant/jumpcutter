#![feature(array_chunks)]
#![feature(array_windows)]

extern crate ffmpeg_next as ffmpeg;

mod args;
mod fcpxml;

use std::io::Write;
use std::path::PathBuf;

use args::Args;
use eyre::{eyre, Result};
use fcpxml::Fcp;
use ffmpeg::codec::context::Context;
use ffmpeg::format::sample;
use ffmpeg::format::Sample;
use ffmpeg::frame::Audio;
use ffmpeg::media::Type;

fn main() -> Result<()> {
    ffmpeg::init().unwrap();

    let args = Args::parse_args();

    // Get audio stream from the file
    let mut ictx = ffmpeg::format::input(&args.input_file)?;
    let audio_input = ictx
        .streams()
        .best(Type::Audio)
        .ok_or(ffmpeg::Error::StreamNotFound)?;
    let audio_stream_index = audio_input.index();
    let audio_context = Context::from_parameters(audio_input.parameters())?;
    let mut audio_decoder = audio_context.decoder().audio()?;

    // Get video for metadata reasons
    let video_input = ictx
        .streams()
        .best(Type::Video)
        .ok_or(ffmpeg::Error::StreamNotFound)?;
    let video_context = Context::from_parameters(video_input.parameters())?;
    let video_decoder = video_context.decoder().video()?;

    let video_frames = video_input.frames() as usize;
    let fps = video_input.rate().0 / video_input.rate().1;
    let height = video_decoder.height();
    let width = video_decoder.width();

    // Get audio volumes from the stream
    let mut volumes: Vec<f64> = vec![];
    for (stream, packet) in ictx.packets() {
        if stream.index() == audio_stream_index {
            audio_decoder.send_packet(&packet)?;
            let mut decoded = Audio::empty();
            while audio_decoder.receive_frame(&mut decoded).is_ok() {
                match decoded.format() {
                    Sample::F32(sample::Type::Planar) => {
                        let mut data = decoded
                            .plane::<f32>(1)
                            .iter()
                            .map(|d| d.abs() as f64)
                            .collect::<Vec<_>>();

                        volumes.append(&mut data);
                    }
                    fmt => {
                        return Err(eyre!("Unrecognized format {:?}", fmt));
                    }
                };
            }
        }
    }
    audio_decoder.send_eof()?;

    // Get the number of frames and get an average of sound for it
    let frame_group = volumes.len() / video_frames;
    let mut means: Vec<f64> = vec![];
    let mut loud = 0f64;
    for data in volumes.chunks(frame_group) {
        // Calculate the average of the volume group
        let avg = data.iter().copied().sum::<f64>() / data.len() as f64;
        means.push(avg);

        let max = data
            .iter()
            .max_by(|a, b| a.partial_cmp(b).unwrap())
            .unwrap_or(&loud);
        if *max > loud {
            loud = *max;
        }
    }

    // Collect edges (where we go from silent to loud or vice versa)
    let mut starts: Vec<usize> = vec![];
    let mut ends: Vec<usize> = vec![];
    let loud_threshold = loud * args.silent_threshold;
    if means[0] > loud_threshold {
        // If the beginning is loud push it
        starts.push(0);
    }
    for (index, &[first, second]) in means.array_windows::<2>().enumerate() {
        if first < loud_threshold && second > loud_threshold {
            // Silent -> loud (start)
            starts.push(index);
        } else if first > loud_threshold && second < loud_threshold {
            // Loud -> silent (end)
            ends.push(index);
        }
    }
    if means[means.len() - 1] < loud_threshold {
        // If the end is silent push it
        starts.push(means.len() - 1);
    }

    let input = PathBuf::from(args.input_file).canonicalize()?;

    let fcp = Fcp::new(
        input.to_string_lossy().to_string(),
        (width as u64, height as u64),
        fps as u64,
        video_frames as u64,
        starts.into_iter().zip(ends).collect::<Vec<_>>(),
    );

    let xmlfile = args.xml_file.unwrap_or_else(|| {
        let xml = input.to_string_lossy().to_string();

        let (start, _) = xml.rsplit_once('.').unwrap_or((&xml, ""));

        format!("{start}.xml")
    });

    let mut output = std::fs::File::create(xmlfile)?;
    output.write_all(fcp.to_string().as_bytes())?;

    Ok(())
}
