#!/usr/bin/env python3
import argparse
import collections
import pathlib
import pprint
import time

import wakepy.keep

import tapas.clips_csv as clips_csv
from tapas.youtube import YouTubeAPIClient

DESCRIPTION_CREDIT = "Published with TAPAS: https://github.com/wecsam/tapas"

def get_clip_description(clip: clips_csv.Clip, suppress_credit: bool):
    if suppress_credit:
        return clip.description

    if clip.description:
        return clip.description + "\n\n" + DESCRIPTION_CREDIT
    return DESCRIPTION_CREDIT

def publish_videos(csv_path: pathlib.Path, playlist_id: str, category_id: str, suppress_credit: bool=False):
    # Build a dictionary of all clips that should be published.
    clips = collections.OrderedDict()
    for clip in clips_csv.read_clips(csv_path):
        clips[clips_csv.get_clip_filename(clip)] = clip

    # Find clips that are already uploaded.
    uploaded = {}
    needs_renaming = set()
    youtube = YouTubeAPIClient()
    for video in youtube.get_uploaded_videos(limit=len(clips)):
        id = video["id"]
        title = video["snippet"]["title"]
        filename = video["fileDetails"]["fileName"]

        if video["processingDetails"]["processingStatus"] != "succeeded":
            print("Ignoring video that is not done processing:", id, filename, title)
            continue

        uploaded[filename] = id

        clip = clips.get(filename)
        if not clip:
            # This video is not a clip from the CSV.
            print("Ignoring video with unrecognized filename:", id, filename, title)
            continue

        print("Discovered uploaded video:", id, filename, title)

        if title != clip.name:
            needs_renaming.add(filename)

    # Assume that videos that need renaming also need to be added to the playlist and published.
    for filename, clip in clips.items():
        video_id = uploaded.get(filename)
        if not video_id:
            print("Video not uploaded or not done processing:", filename, clip.name)
            break

        if filename not in needs_renaming:
            print("Already renamed:", video_id, clip.name)
            continue

        print("Renaming:", video_id, clip.name)
        result = youtube.update_video(
            video_id,
            {
                "snippet": {
                    "title": clip.name,
                    "description": get_clip_description(clip, suppress_credit),
                    "categoryId": category_id
                },
                "status": {
                    "privacyStatus": "public"
                }
            }
        )
        if not result.get("id"):
            pprint(result)
            return

        print("Adding it to the playlist")
        result = youtube.add_video_to_playlist(playlist_id, video_id)
        if not result.get("id"):
            pprint(result)
            return

        time.sleep(0.1) # extremely conservative API rate limit

def parse_args():
    parser = argparse.ArgumentParser(
        prog="publish_videos.py",
        description=
            "Renames videos on YouTube using names from a CSV file. Adds them to a playlist. Sets their privacy to "
            "Public."
    )
    parser.add_argument(
        "csv_path",
        type=pathlib.Path,
        help="the path to the CSV file of the videos (see README.md for what columns to include)"
    )
    parser.add_argument(
        "playlist_id",
        help="the ID of the playlist on YouTube"
    )
    parser.add_argument(
        "--category-id",
        default="22",
        help="the YouTube category ID to assign to videos (default: 22)"
    )
    parser.add_argument(
        "--suppress-credit",
        action="store_true",
        help="suppresses the line of text that credits TAPAS at the end of the description"
    )
    return parser.parse_args()

if __name__ == "__main__":
    with wakepy.keep.running():
        publish_videos(**vars(parse_args()))
