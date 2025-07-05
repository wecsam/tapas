#!/usr/bin/env python3
import csv
import sys
import time

from tapas.youtube import YouTubeAPIClient, walk_dict

COLUMNS = (
    ("id",),
    ("snippet", "resourceId", "kind"),
    ("snippet", "resourceId", "videoId"),
    ("snippet", "title"),
    ("contentDetails", "note"),
)

def playlist_to_csv(playlist_id: str, csv_path: str):
    items = [(item["snippet"]["position"], [
        walk_dict(item, *path) for path in COLUMNS
    ]) for item in YouTubeAPIClient().get_playlist_items(playlist_id)]
    items.sort()

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(".".join(path) for path in COLUMNS)
        for _, row in items:
            writer.writerow(row)

def csv_to_playlist(csv_path: str, playlist_id: str):
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        client = YouTubeAPIClient()
        for position, row in enumerate(csv.DictReader(f)):
            title = row[".".join(COLUMNS[3])]

            print("Moving", title, "to position", position)
            client.update_playlist_item(
                playlist_id=playlist_id,
                playlist_item_id=row[".".join(COLUMNS[0])],
                resource_kind=row[".".join(COLUMNS[1])],
                video_id=row[".".join(COLUMNS[2])],
                position=position,
                note=row[".".join(COLUMNS[4])]
            )

            # Rate limit to avoid hitting per-minute API quota
            time.sleep(0.000001)

def main():
    if len(sys.argv) != 4 or sys.argv[2] not in ("to_csv", "to_playlist"):
        print("Dump a YouTube playlist into a CSV file:", file=sys.stderr)
        print("Usage:", sys.argv[0], "PLAYLIST_ID", "to_csv", "CSV_PATH", file=sys.stderr)
        print("Update a YouTube playlist based on a CSV file:", file=sys.stderr)
        print("Usage:", sys.argv[0], "CSV_PATH", "to_playlist", "PLAYLIST_ID", file=sys.stderr)
        return

    if sys.argv[2] == "to_csv":
        playlist_to_csv(sys.argv[1], sys.argv[3])
    else:
        csv_to_playlist(sys.argv[1], sys.argv[3])

if __name__ == "__main__":
    main()
