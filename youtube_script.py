import json
import os
import time
import random
import httplib2
from http import client

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pytube import YouTube

CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/youtube"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"


class YoutubeManager:
    def __init__(self):
        self.youtube = self.get_authenticated_service()

    def get_authenticated_service(self):
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CLIENT_SECRETS_FILE, SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        return build(API_SERVICE_NAME, API_VERSION, credentials=creds)

    def playlist_list(self, channelId):
        full_list = []
        playlists = self.youtube.playlists()
        request = playlists.list(
            part="id,contentDetails,snippet,status",
            channelId=channelId,
            maxResults=50,
        )
        while request is not None:
            playlist_tracks = request.execute()
            full_list.extend(playlist_tracks["items"])
            request = playlists.list_next(request, playlist_tracks)
        return full_list

    def playlist_elements(self, playlist_id):
        full_list = []
        playlistItems = self.youtube.playlistItems()
        request = playlistItems.list(
            part="id,contentDetails,snippet,status",
            playlistId=playlist_id,
            maxResults=50,
        )
        while request is not None:
            playlist_tracks = request.execute()
            full_list.extend(playlist_tracks["items"])
            request = playlistItems.list_next(request, playlist_tracks)
        return full_list

    def playlistItems_position(
        self, id_: int, place_num: int, video_id: str, playlist_id: str
    ):
        request = self.youtube.playlistItems().update(
            part="snippet",
            body={
                "id": id_,
                "snippet": {
                    "playlistId": playlist_id,
                    "position": place_num,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id,
                    },
                },
            },
        )
        response = request.execute()
        return response

    def playlistItems_insert(self, playlist_id: int, video_id: str, position: int):
        request = self.youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "position": position,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id,
                    },
                },
            },
        )
        response = request.execute()
        return response

    def video_insert(self, file: os.PathLike):
        #! check if exist ?
        # tags = None
        # if options.keywords:
        #     tags = options.keywords.split(",")
        body = {
            "snippet": {
                "title": "TITLE TEST TITLE",
                "description": "DESCRIPTION",
                "tags": None,
                "categoryId": "22",
            },
            "status": {"privacyStatus": "private"},
        }

        insert_request = self.youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=MediaFileUpload(file, chunksize=-1, resumable=True),
        )

        return self._resumable_upload(insert_request)

    def _resumable_upload(self, request):
        RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
        RETRIABLE_EXCEPTIONS = (
            httplib2.HttpLib2Error,
            IOError,
            client.NotConnected,
            client.IncompleteRead,
            client.ImproperConnectionState,
            client.CannotSendRequest,
            client.CannotSendHeader,
            client.ResponseNotReady,
            client.BadStatusLine,
        )
        MAX_RETRIES = 10
        httplib2.RETRIES = 1

        response = None
        error = None
        retry = 0
        while response is None:
            try:
                print("Uploading file...")
                status, response = request.next_chunk()
                if response is not None:
                    if "id" in response:
                        print(
                            'Video id "%s" was successfully uploaded.' % response["id"]
                        )
                        return response["id"]
                    else:
                        exit(
                            "The upload failed with an unexpected response: %s"
                            % response
                        )
            except HttpError as e:
                if e.resp.status in RETRIABLE_STATUS_CODES:
                    error = "A retriable HTTP error %d occurred:\n%s" % (
                        e.resp.status,
                        e.content,
                    )
                else:
                    raise
            except RETRIABLE_EXCEPTIONS as e:
                error = "A retriable error occurred: %s" % e

            if error is not None:
                print(error)
                retry += 1
                if retry > MAX_RETRIES:
                    exit("No longer attempting to retry.")

                max_sleep = 2**retry
                sleep_seconds = random.random() * max_sleep
                print("Sleeping %f seconds and then retrying..." % sleep_seconds)
                time.sleep(sleep_seconds)

    def download_video(self, video_id):
        yt = YouTube(f"http://youtube.com/watch?v={video_id}")
        yt.streams.order_by("resolution").desc().first().download(
            filename_prefix=f"{video_id}_"
        )


def main():
    yt_manager = YoutubeManager()

    # test for loading all items from playlist
    # if not os.path.exists("playlist.json"):
    #     all_videos = yt_manager.get_playlist("PLomXEcQ9kTsHrH58bvsUSfBT1PhZLc5MX")
    #     print(all_videos)

    #     with open("playlist.json", "w") as f:
    #         json.dump(all_videos, f, indent=4)
    # else:
    #     with open("playlist.json", "r") as f:
    #         all_videos = json.load(f)
    #     print(all_videos)

    # test for changing position of video in playlist
    # yt_manager.position_video(
    #     "UExvbVhFY1E5a1RzSHJINThidnNVU2ZCVDFQaFpMYzVNWC41NkI0NEY2RDEwNTU3Q0M2",
    #     1,
    #     "_FklT0OQZKA",
    #     "PLomXEcQ9kTsHrH58bvsUSfBT1PhZLc5MX",
    # )

    # test for uploading video
    # all_playlists = yt_manager.all_playlist("UCB77PqR0FaPGptCiO27KFCg")
    # with open("all_playlists.json", "w") as f:
    #     json.dump(all_playlists, f, indent=4)
    # video_id = yt_manager.upload_video("test_file.mp4")

    # test for inserting video to playlist
    # yt_manager.playlistItems_insert("PLomXEcQ9kTsHrH58bvsUSfBT1PhZLc5MX", video_id, 0)

    # test for downloading video
    # yt_manager.download_video(video_id)


if __name__ == "__main__":
    main()
