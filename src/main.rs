#![feature(array_chunks)]
#![feature(array_windows)]

extern crate ffmpeg_next as ffmpeg;

mod args;

use args::Args;
use eyre::{eyre, Result};
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

    let video_input = ictx
        .streams()
        .best(Type::Video)
        .ok_or(ffmpeg::Error::StreamNotFound)?;
    let video_frames = video_input.frames().abs() as usize;

    let context_decoder =
        ffmpeg::codec::context::Context::from_parameters(audio_input.parameters())?;
    let mut decoder = context_decoder.decoder().audio()?;

    // Get audio volumes from the stream
    let mut volumes: Vec<f64> = vec![];
    for (stream, packet) in ictx.packets() {
        if stream.index() == audio_stream_index {
            decoder.send_packet(&packet)?;
            let mut decoded = Audio::empty();
            while decoder.receive_frame(&mut decoded).is_ok() {
                match decoded.format() {
                    Sample::F32(sample::Type::Planar) => {
                        let mut data = decoded
                            .plane::<f32>(1)
                            .into_iter()
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
    decoder.send_eof()?;

    // Get the number of frames and get an average of sound for it
    let frame_group = volumes.len() / video_frames;
    let mut means: Vec<f64> = vec![];
    let mut loud = 0f64;
    for data in volumes.chunks(frame_group) {
        // Calculate the average of the volume group
        let avg = data.into_iter().map(|d| *d).sum::<f64>() / data.len() as f64;
        means.push(avg);

        let max = data
            .into_iter()
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

    for (start, end) in starts.into_iter().zip(ends) {
        println!("loud part: {start} {end}");
    }

    Ok(())
}
