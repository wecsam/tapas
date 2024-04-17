# Time Adjacent Playlist Assembly System
This repository contains a set of scripts that help you take long videos, split them into smaller videos, upload those
smaller videos to YouTube, and then publish those videos in a playlist on YouTube.

## Setup
This project targets Python 3.12.

Install required libraries:

    pip install -r requirements.txt

Install [`ffmpeg`](https://ffmpeg.org/) and add it and `ffprobe` to your `PATH`.

Set up the YouTube Data API client:
1. Create or select a project in the [Google API Console](https://console.cloud.google.com/).
2. In the [library panel](https://console.developers.google.com/apis/library), ensure that the **YouTube Data API v3**
   is enabled.
3. In the [credentials panel](https://console.developers.google.com/apis/credentials), create an
   **OAuth 2.0 client ID** and download the JSON file with your client secrets.
4. Store the path to the client secrets JSON file in an environment variable called `GOOGLE_CLIENT_SECRETS_FILE`.

## Suggested Workflow
You will need enough storage space to store a copy of the footage from the camera and to store clips from the footage.

1. If the camera split videos into multiple files, recombine them. For example, the DJI Osmo Action splits video files
   every 4 GB; run [dji_concat.py](dji_concat.py) to concatenate the 4 GB segments back into full videos.
2. Use your favorite spreadsheet application to create a CSV file with timestamps at which the videos should be split.
   It should have the following columns (other columns will be ignored):
    * **File**: specify the path, relative to the CSV file, of the video to split into smaller clips.
    * **Inpoint**: specify the time in the video at which the clip should start. The clip will end at the next clip's
      inpoint. You can use any string that [pytimeparse](https://github.com/onegreyonewhite/pytimeparse2) recognizes.
    * **Name**: specify the name to use for the clip after it is uploaded to YouTube. This does not affect the filename
      of the clip.
    * **Description**: specify a description for clip after it is uploaded to YouTube. This column is optional.
    * **Skip**: put any string of text to skip saving a file for this clip. This column is optional.
3. Run [clip_videos.py](clip_videos.py) to split the full videos into clips. Although the script supports making some
   clips, getting an updated CSV file, and then making more clips, it is recommended that you make clips from an entire
   full video at once. That is because `ffmpeg` must read the video file from the beginning every time that you run it;
   making some clips from the start of the video, stopping, and then making more clips from the end of the video is not
   efficient.
4. Upload the clips to YouTube. Do not rename them before uploading; their original filenames will be used to identify
   them when publishing them.
5. Create an empty playlist on YouTube. Note its ID from the URL.
6. Run [publish_videos.py](publish_videos.py). It will rename the videos to match the **Name** column in your CSV
   file, add the descriptions from the **Descriptions** column, add the videos to the playlist, and change the privacy
   from **Draft** to **Public**.
