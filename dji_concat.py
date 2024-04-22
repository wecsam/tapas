#!/usr/bin/env python3
import argparse
import collections
import pathlib
import shutil
import typing

import wakepy.keep

import tapas.ffmpeg as ffmpeg

def dji_concat(dir_in: pathlib.Path, dir_out: typing.Optional[pathlib.Path]):
    if dir_out is None:
        dir_out = dir_in

    if not dir_in.is_dir():
        print("Error: dir_in does not exist")
        return

    if not dir_out.is_dir():
        print("Error: dir_out does not exist")
        return

    files_to_concat = collections.defaultdict(list)
    for file in dir_in.iterdir():
        if not file.is_file():
            continue

        name_parts = file.name.split("_")
        if not name_parts or name_parts[0] != "DJI":
            continue

        if len(name_parts) == 3: # DJI_1234_123.MP4
            files_to_concat[name_parts[1]].append(name_parts[2])
        else: # DJI_1234.MP4
            print("Copying:", file)
            try:
                shutil.copy2(file, dir_out.joinpath(file.name))
            except shutil.SameFileError:
                print("Copying aborted because source and destination are the same")

    for name_middle, name_suffixes in files_to_concat.items():
        out_name = "DJI_{}.MP4".format(name_middle)
        print("Concatenating:", out_name)
        name_suffixes.sort()
        ffmpeg.concat(
            [dir_in.joinpath("DJI_{}_{}".format(name_middle, name_suffix)) for name_suffix in name_suffixes],
            dir_out.joinpath(out_name)
        )

def parse_args():
    parser = argparse.ArgumentParser(
        prog="dji_concat.py",
        description=
            "Takes files from the same recording session on the DJI Osmo Action and recombines them. For example, it "
            "will combine DJI_1234_001.MP4, DJI_1234_002.MP4, DJI_1234_003.MP4, etc. into DJI_1234.MP4."
    )
    parser.add_argument(
        "dir_in",
        type=pathlib.Path,
        help="the path to the directory that contains the original files from the camera"
    )
    parser.add_argument(
        "dir_out",
        type=pathlib.Path,
        nargs="?",
        help="the path to the directory where the concatenated files should be placed (default: same as dir_in)"
    )
    return parser.parse_args()

if __name__ == "__main__":
    with wakepy.keep.running():
        dji_concat(**vars(parse_args()))
