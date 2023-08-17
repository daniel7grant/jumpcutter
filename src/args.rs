use clap::Parser;

#[derive(Debug, Parser)]
#[command(author, version, about, long_about = None)]
pub struct Args {
    /// the video file you want modified
    #[arg(long)]
    pub input_file: String,
    /// the XML timeline output. (default: the input file's name + .xml)
    #[arg(long)]
    pub xml_file: Option<String>,
    /// the volume amount that frames' audio needs to surpass to be consider \"sounded\". It ranges from 0 (silence) to 1 (max volume)
    #[arg(long, default_value_t = 0.03)]
    pub silent_threshold: f64,
    /// some silent frames adjacent to sounded frames are included to provide context. How many frames on either the side of speech should be included? That's this variable.
    #[arg(long, default_value_t = 0)]
    pub frame_margin: usize,
}

impl Args {
    pub fn parse_args() -> Self {
        Args::parse()
    }
}
