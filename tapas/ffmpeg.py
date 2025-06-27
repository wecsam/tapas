#!/usr/bin/env python3
import datetime
import json
import pathlib
import shlex
import subprocess
import sys
import tempfile
from typing import List, Optional

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

def get_format_tags(file: pathlib.Path) -> dict:
    return json.loads(
        subprocess.run(
            ["ffprobe", "-v", "quiet", str(file), "-show_entries", "format_tags", "-print_format", "json"],
            capture_output=True,
            encoding=sys.getdefaultencoding()
        ).stdout
    ).get("format", {}).get("tags", {})

def get_creation_time(file: pathlib.Path) -> Optional[datetime.datetime]:
    creation_time_str = get_format_tags(file).get("creation_time")
    if creation_time_str:
        return parse_dt(creation_time_str)
    return None

def parse_dt(s: str) -> datetime.datetime:
    # The UTC time zone can be added because TIMESTAMP_FORMAT contains "Z" at the end.
    return datetime.datetime.strptime(s, TIMESTAMP_FORMAT).replace(tzinfo=datetime.timezone.utc)

def format_dt(dt: datetime.datetime) -> str:
    return dt.astimezone(datetime.timezone.utc).strftime(TIMESTAMP_FORMAT)

def concat(files_in: List[pathlib.Path], file_out: pathlib.Path) -> None:
    if not files_in:
        raise ValueError("files_in cannot be empty")

    creation_time = get_creation_time(files_in[0])

    with tempfile.NamedTemporaryFile("w") as concat_file:
        for file in files_in:
            print("file", shlex.quote(str(file.absolute())), file=concat_file)
        concat_file.flush()

        args = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_file.name]
        if creation_time:
            args.extend(["-metadata", f"creation_time={format_dt(creation_time)}"])
        args.extend(["-c", "copy", str(file_out.absolute())])
        subprocess.run(args).check_returncode()

if __name__ == "__main__":
    print("This is a library. It cannot be run directly.")
