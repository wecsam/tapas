#!/usr/bin/env python3
import argparse
import collections
import datetime
import pathlib
import shlex
import subprocess

import wakepy.keep

import tapas.clips_csv as clips_csv
import tapas.ffmpeg as ffmpeg

def clip_videos(csv_path: pathlib.Path, output_dir: pathlib.Path, encode=False):
    if not output_dir.is_dir():
        print("Error: output_dir does not exist")
        return

    clips_from_file = collections.defaultdict(list)
    for clip in clips_csv.read_clips(csv_path):
        clips_from_file[clip.file].append(clip)

    output_dir.mkdir(exist_ok=True)
    for file, clips in clips_from_file.items():
        file_path = csv_path.parent.joinpath(file)
        original_creation_time = ffmpeg.get_creation_time(file_path)

        args = ["ffmpeg"]
        if encode:
            args.extend(("-hwaccel", "auto"))
        args.extend(["-i", str(file_path)])

        exec_ffmpeg = False
        for clip in clips:
            filename = clips_csv.get_clip_filename(clip)
            clip_path = output_dir.joinpath(filename)
            if clip_path.exists():
                print("Already exists:", clip_path)
                continue
            print("Clipping:", filename, datetime.timedelta(seconds=clip.outpoint - clip.inpoint))
            exec_ffmpeg = True

            if encode:
                args.extend(("-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p"))
                args.extend(("-movflags", "+faststart"))
                args.extend(("-c:a", "aac", "-b:a", "192k"))
            else:
                args.extend(("-c", "copy"))

            if original_creation_time:
                creation_time = original_creation_time + datetime.timedelta(seconds=clip.inpoint)
                args.extend(["-metadata", f"creation_time={ffmpeg.format_dt(creation_time)}"])

            args.extend(["-ss", str(clip.inpoint), "-to", str(clip.outpoint), str(clip_path)])

        if exec_ffmpeg:
            print("Executing:", shlex.join(args))
            subprocess.run(args)

def parse_args():
    parser = argparse.ArgumentParser(
        prog="clip_videos.py",
        description="Clips videos into smaller videos using cut points from a CSV file."
    )
    parser.add_argument(
        "csv_path",
        type=pathlib.Path,
        help="the path to the CSV file of clips to make (see README.md for what columns to include)"
    )
    parser.add_argument(
        "output_dir",
        type=pathlib.Path,
        help="the path to the directory in which to place the smaller videos"
    )
    parser.add_argument(
        "-e", "--encode",
        action="store_true",
        help="if set, re-encode video and audio instead of stream copying"
    )
    return parser.parse_args()

if __name__ == "__main__":
    with wakepy.keep.running():
        clip_videos(**vars(parse_args()))
