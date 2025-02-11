#!/usr/bin/env python3
import collections
import csv
import itertools
import pathlib
from typing import Generator

import pytimeparse

Clip = collections.namedtuple(
    "Clip",
    (
        "file",
        "inpoint",
        "outpoint",
        "name",
        "description"
    )
)

def get_clip_filename(clip: Clip) -> str:
    return f"{clip.file.stem}-{clip.inpoint}-{clip.outpoint}{clip.file.suffix}"

def parse_timecode(s: str) -> int | float | None:
    '''
    Tries to parse a time expression as a number of seconds.
    Returns None if the string cannot be parsed.
    '''
    try:
        return float(s)
    except ValueError:
        return pytimeparse.parse(s)

def read_clips(csv_path: pathlib.Path) -> Generator[Clip, None, None]:
    with open(csv_path, "r", newline="") as fin:
        for row_number, (this_row, next_row) in enumerate(itertools.pairwise(csv.DictReader(fin)), 2):
            if this_row.get("Skip"):
                continue

            file = this_row.get("File")
            if not file:
                print(f"Row {row_number} error: File missing")
                break

            if file != next_row.get("File"):
                continue

            file = pathlib.PurePath(file)

            inpoint = this_row.get("Inpoint")
            if not inpoint:
                print(f"Row {row_number} error: Inpoint missing")
                break
            inpoint = parse_timecode(inpoint)
            if inpoint is None:
                print(f"Row {row_number} error: invalid format for Inpoint")
                break

            outpoint = next_row.get("Inpoint")
            if not outpoint:
                print(f"Row {row_number} error: next row's Inpoint missing")
                break
            outpoint = parse_timecode(outpoint)
            if outpoint is None:
                print(f"Row {row_number} error: invalid format for Inpoint on next row")

            if inpoint >= outpoint:
                print(f"Row {row_number} error: Inpoint is not less than next row's Inpoint")
                break

            name = this_row.get("Name")
            if not name:
                print(f"Row {row_number} error: Name missing")
                break

            description = this_row.get("Description", "")

            yield Clip(file, inpoint, outpoint, name, description)

if __name__ == "__main__":
    print("This is a library. It cannot be run directly.")
