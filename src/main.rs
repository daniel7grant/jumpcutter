#![feature(array_chunks)]
#![feature(array_windows)]

extern crate ffmpeg_next as ffmpeg;

mod args;

use args::Args;
use eyre::Result;
use ffmpeg::frame::Audio;
use ffmpeg::media::Type;

fn main() -> Result<()> {
    ffmpeg::init().unwrap();

    let args = Args::parse_args();

    // Get audio stream from the file
    let mut ictx = ffmpeg::format::input(&args.input_file)?;
    let input = ictx
        .streams()
        .best(Type::Audio)
        .ok_or(ffmpeg::Error::StreamNotFound)?;
    let audio_stream_index = input.index();

    let context_decoder = ffmpeg::codec::context::Context::from_parameters(input.parameters())?;
    let mut decoder = context_decoder.decoder().audio()?;

    // Get audio volumes from the stream
    let mut volumes: Vec<f64> = vec![];
    let mut loud = 0 as f64;
    for (stream, packet) in ictx.packets() {
        if stream.index() == audio_stream_index {
            decoder.send_packet(&packet)?;
            let mut decoded = Audio::empty();
            while decoder.receive_frame(&mut decoded).is_ok() {
                let data = decoded
                    .data(0)
                    .array_chunks::<8>()
                    .map(|chunk| i64::from_be_bytes(*chunk).abs() as u64)
                    .collect::<Vec<u64>>();

                // Calculate the average of the volume
                let avg = data
                    .clone()
                    .into_iter()
                    .map(|d| d as u128)
                    .sum::<u128>() as f64
                    / data.len() as f64;
                volumes.push(avg);

                // Calculate the max volume for a loud treshold
                let local_loud = data
                    .into_iter()
                    .max()
                    .map(|m| m as f64)
                    .unwrap_or(loud);
                if local_loud > loud {
                    loud = local_loud;
                }
            }
        }
    }
    decoder.send_eof()?;

    println!("{:?}, {}", volumes.len(), loud);

    // Collect edges (where we go from silent to loud or vice versa)
    let mut starts: Vec<usize> = vec![];
    let mut ends: Vec<usize> = vec![];
    for (index, &[first, second]) in volumes.array_windows::<2>().enumerate() {
        if first > loud && second < loud {
            starts.push(index);
        } else if first > loud && second < loud {
            ends.push(index);
        }
    }

    for (start, end) in starts.into_iter().zip(ends) {
        println!("loud part: {start} {end}");
    }

    Ok(())
}
