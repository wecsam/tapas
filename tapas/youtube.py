#!/usr/bin/env python3
import collections
import json
import os
from typing import Any, Callable, Dict, Generator, Iterable, Optional

import google_auth_oauthlib.flow
import googleapiclient.discovery

class YouTubeAPIClient:
    CACHE_FILE = "youtube-cache.json"

    def __init__(self):
        self.client = googleapiclient.discovery.build(
            "youtube",
            "v3",
            credentials=google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                self.get_client_secrets_file(),
                ["https://www.googleapis.com/auth/youtube"]
            ).run_local_server(open_browser=False)
        )

        try:
            with open(self.CACHE_FILE, "r") as f:
                self.cache = json.load(f)
        except FileNotFoundError:
            self.cache = {}

    def __del__(self):
        cache = getattr(self, "cache", None)
        if cache:
            with open(self.CACHE_FILE, "w") as f:
                json.dump(cache, f, indent=4)

    def get_uploaded_videos(self, limit: Optional[int]=None) -> Generator[dict, None, None]:
        '''
        Gets the user's uploads.
        '''
        uploads_playlist_id = self.client.channels().list(
            part="contentDetails",
            mine=True
        ).execute()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        return self.get_playlist_videos(uploads_playlist_id, limit=limit)

    def get_playlist_videos(self, playlist_id: str, limit: Optional[int]=None) -> Generator[dict, None, None]:
        '''
        Gets the videos from a playlist.
        '''
        if limit is None:
            limit = -1
        elif limit < 0:
            return

        # The generator first gets playlist items, each of which as a video ID.
        # Then, get_videos gets the video for each video ID.
        for video in self.get_videos(
            playlist_item["contentDetails"]["videoId"] for playlist_item in self.concat_page_items(
                lambda next_page_token: self.client.playlistItems().list(
                    part="contentDetails",
                    maxResults=50,
                    pageToken=next_page_token,
                    playlistId=playlist_id
                )
            )
        ):
            if limit == 0:
                break
            limit -= 1

            yield video

    def get_videos(self, video_ids: Iterable[str]) -> Generator[dict, None, None]:
        '''
        Given some video IDs, gets videos. Videos are cached.
        Videos may not be yielded in the same order as their IDs were given.
        '''
        if "videos" not in self.cache:
            self.cache["videos"] = {}

        buffer = []
        def process_buffer():
            id = ",".join(buffer)
            buffer.clear()

            videos = []
            for video in self.concat_page_items(
                lambda next_page_token: self.client.videos().list(
                    part="snippet,contentDetails,fileDetails,processingDetails",
                    maxResults=50,
                    pageToken=next_page_token,
                    id=id
                )
            ):
                print("Got video info from API:", video["id"], video["fileDetails"]["fileName"], video["snippet"]["title"])
                self.cache["videos"][video["id"]] = video
                videos.append(video)
                # We make a list of videos instead of yielding them because we want the caching to happen
                # even if the video isn't used/consumed.

            return videos

        for id in video_ids:
            video = self.cache["videos"].get(id)
            if video and video["processingDetails"]["processingStatus"] != "processing":
                print("Got video info from cache:", id, video["fileDetails"]["fileName"], video["snippet"]["title"])
                yield video
                continue

            buffer.append(id)
            if len(buffer) == 50:
                for video in process_buffer(): yield video

        for video in process_buffer(): yield video

    def update_video(self, video_id: str, body: dict) -> dict:
        '''
        Updates a video's snippet, including its title and description. Sets the video to public.
        Updates the cache.
        '''
        part = ",".join(body.keys())
        body["id"] = video_id

        try:
            video = self.cache["videos"][video_id]
        except KeyError: pass
        else:
            update_deep(video, body)

        return self.client.videos().update(part=part, body=body).execute()

    def add_video_to_playlist(self, playlist_id: str, video_id: str) -> dict:
        '''
        Adds a video to a playlist.
        '''
        return self.client.playlistItems().insert(
            part="snippet",
            body={
              "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                  "kind": "youtube#video",
                  "videoId": video_id
                }
              }
            }
        ).execute()

    @staticmethod
    def concat_page_items(get_request: Callable[[Optional[str]], Any]) -> Generator[dict, None, None]:
        '''
        Automatically executes a request and repeats it with each nextPageToken.
        '''
        next_page_token = None
        while True:
            result = get_request(next_page_token).execute()

            for item in result["items"]:
                yield item

            next_page_token = result.get("nextPageToken")
            if not next_page_token:
                # There is no next page.
                return

    @staticmethod
    def get_client_secrets_file() -> str:
        '''
        Gets the location of the client secrets file.
        '''
        return os.environ["GOOGLE_CLIENT_SECRETS_FILE"]

def update_deep(d: Dict, u: Dict) -> Dict:
    '''
    Updates a dict deeply.
    '''
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = update_deep(d.get(k, {}), v)
        else:
            d[k] = v
    return d

if __name__ == "__main__":
    print("This is a library. It cannot be run directly.")
