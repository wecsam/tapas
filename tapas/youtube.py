#!/usr/bin/env python3
import collections
import collections.abc
import json
import os
from typing import Any, Callable, Dict, Generator, Iterable, Optional

import google_auth_oauthlib.flow
import googleapiclient.discovery

class YouTubeAPIClient:
    CACHE_FILE = "youtube-cache.json"

    class VideoGetter:
        '''
        Given some video IDs, gets videos. Uses a cache.
        Videos are returned by __next__ in the order in which their IDs were given.
        '''

        def __init__(self, parent: "YouTubeAPIClient", video_ids: Iterable[str]):
            self._parent = parent
            self._ids_to_get = iter(video_ids)
            self._videos_to_return_values_iter = None

        def __iter__(self):
            return self

        def __next__(self) -> dict:
            if self._videos_to_return_values_iter is not None:
                try:
                    return next(self._videos_to_return_values_iter)
                except StopIteration:
                    self._videos_to_return_values_iter = None

            cache = self.get_cache()
            videos_to_return = collections.OrderedDict()
            ids_to_get_from_api = []
            while len(ids_to_get_from_api) != 50:
                try:
                    id = next(self._ids_to_get)
                except StopIteration:
                    break

                video = cache.get(id)
                processing_status = walk_dict(video, "processingDetails", "processingStatus")
                if processing_status and processing_status != "processing":
                    # The video is in the cache. If there are no videos to get from the API, this is the next video to
                    # return. It can be returned immediately. Otherwise, it should be queued to be returned after the
                    # other videos are gotten from the API.
                    if not ids_to_get_from_api:
                        return video
                    videos_to_return[id] = video
                else:
                    videos_to_return[id] = None
                    ids_to_get_from_api.append(id)

            if not videos_to_return:
                raise StopIteration

            if ids_to_get_from_api:
                # Get videos from the API.
                ids_joined = ",".join(ids_to_get_from_api)
                for video in self._parent.concat_page_items(
                    lambda next_page_token: self._parent.client.videos().list(
                        part="snippet,contentDetails,fileDetails,processingDetails",
                        maxResults=50,
                        pageToken=next_page_token,
                        id=ids_joined
                    )
                ):
                    id = video["id"]
                    cache[id] = video
                    if id in videos_to_return:
                        videos_to_return[id] = video

                for id, video in videos_to_return.items():
                    if video is None:
                        raise ValueError(f"Unknown video ID {id}")

            self._videos_to_return_values_iter = iter(videos_to_return.values())
            return next(self._videos_to_return_values_iter)

        def get_cache(self) -> dict:
            cache = self._parent.cache.get("videos")
            if not isinstance(cache, dict):
                cache = {}
                self._parent.cache["videos"] = cache
            return cache

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
            playlist_item["contentDetails"]["videoId"] for playlist_item in self.get_playlist_items(playlist_id)
        ):
            if limit == 0:
                break
            limit -= 1

            yield video

    def get_playlist_items(self, playlist_id: str) -> Generator[dict, None, None]:
        '''
        Gets the playlist items from the playlist.
        This does not retrieve all video details; for that, use `get_playlist_videos`.
        '''
        return self.concat_page_items(
            lambda next_page_token: self.client.playlistItems().list(
                part="contentDetails,snippet",
                maxResults=50,
                pageToken=next_page_token,
                playlistId=playlist_id
            )
        )

    def get_videos(self, video_ids: Iterable[str]) -> VideoGetter:
        '''
        Given some video IDs, gets videos. Videos are cached.
        Videos are yielded in the same order in which their IDs were given.
        '''
        return self.VideoGetter(self, video_ids)

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

def walk_dict(d: Dict, *args: Any) -> Any:
    '''
    Walks down nested mappings. Calling walk_dict(d, 1, 2, 3) is the same as getting d[1][2][3], except that if any
    subscript can't be gotten, None is returned.
    '''
    for key in args:
        if not isinstance(d, collections.abc.Mapping):
            return None

        d = d.get(key)

    return d

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
