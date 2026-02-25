#!/usr/bin/env python3
import csv
from dataclasses import dataclass
import itertools
import pathlib
import re
from typing import Generator

import pytimeparse

CHARS_THAT_YOUTUBE_REMOVES = re.compile(r"[\.\-_]")

@dataclass(frozen=True)
class Clip:
    '''
    The file to clip from, the in and out points in seconds, the name and description of the clip.
    '''
    file: pathlib.PurePath
    inpoint: float
    outpoint: float
    name: str
    description: str

    def get_clip_filename(self) -> str:
        '''
        Returns a filename for the clip, based on the source file name and the in and out points.
        '''
        inpoint_str = self._format_seconds(self.inpoint)
        outpoint_str = self._format_seconds(self.outpoint)
        return f"{self.file.stem}-{inpoint_str}-{outpoint_str}{self.file.suffix}"

    def get_expected_youtube_title(self) -> str:
        '''
        Returns the expected YouTube title for the clip, based on filename.
        '''
        cleaned_stem = CHARS_THAT_YOUTUBE_REMOVES.sub(" ", self.file.stem)
        inpoint_str = self._format_seconds(self.inpoint)
        outpoint_str = self._format_seconds(self.outpoint)
        return f"{cleaned_stem} {inpoint_str} {outpoint_str}"

    @staticmethod
    def _format_seconds(seconds: float) -> str:
        '''
        `seconds` is the value of either `inpoint` or `outpoint`. Returns `seconds` formatted such that it can be used
        in a filename and not be mangled when YouTube generates a video title from the filename.
        '''
        return str(int(round(seconds * 100)))

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
    with open(csv_path, "r", newline="", encoding="utf-8") as fin:
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
                break

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
