#!/usr/bin/env python3
import argparse
import collections
import pathlib
import pprint
import time

from wakepy import keep

import tapas.clips_csv as clips_csv
from tapas.youtube import YouTubeAPIClient

DESCRIPTION_CREDIT = "Published with TAPAS: https://github.com/wecsam/tapas"

def get_clip_description(clip: clips_csv.Clip, suppress_credit: bool):
    if suppress_credit:
        return clip.description

    if clip.description:
        return clip.description + "\n\n" + DESCRIPTION_CREDIT
    return DESCRIPTION_CREDIT

def publish_videos(
        csv_path: pathlib.Path, playlist_id: str, category_id: str, uploads_playlist_id="", scan_more_uploads=0,
        suppress_credit=False):
    # Build a dictionary of all clips that should be published.
    clips = collections.OrderedDict[str, clips_csv.Clip]()
    for clip in clips_csv.read_clips(csv_path):
        clips[clip.get_expected_youtube_title()] = clip

    # Find clips that are already uploaded.
    uploaded: dict[str, str] = {} # title -> video ID
    youtube = YouTubeAPIClient()
    uploaded_videos = (youtube.get_playlist_videos(uploads_playlist_id)
                       if uploads_playlist_id else
                       youtube.get_uploaded_videos(limit=len(clips) + scan_more_uploads))
    for video in uploaded_videos:
        id = video["id"]
        title = video["snippet"]["title"]

        if video["processingDetails"]["processingStatus"] != "succeeded":
            print("Ignoring video that is not done processing:", id, title)
            continue

        uploaded[title] = id

        clip = clips.get(title)
        if not clip:
            # This video is not a clip from the CSV.
            print("Ignoring video with unrecognized title:", id, title)
            continue

        print("Discovered uploaded video:", id, title)

    # Assume that videos that need renaming also need to be added to the playlist and published.
    for title, clip in clips.items():
        video_id = uploaded.get(clip.name)
        if video_id:
            print("Already renamed:", video_id, clip.name)
            continue

        video_id = uploaded.get(title)
        if not video_id:
            print("Video not uploaded or not done processing:", title, clip.name)
            break

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
            "Public. By default, this script only looks at the last n uploaded videos, where n is the number of "
            "videos in the CSV. Specify --scan-more-uploads to increase this number."
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
        "--uploads-playlist-id", "-u",
        help="the ID of a playlist to scan instead of your uploaded videos"
    )
    parser.add_argument(
        "--scan-more-uploads",
        type=int,
        default=0,
        help="the number of additional uploads to discover (ignored if --uploads-playlist-id is passed)"
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
    with keep.running():
        publish_videos(**vars(parse_args()))
