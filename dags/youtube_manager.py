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
from pytube.innertube import _default_clients

_default_clients["ANDROID_MUSIC"] = _default_clients["ANDROID_EMBED"]

from dotenv import load_dotenv, find_dotenv
import requests

CLIENT_SECRETS_FILE = "dags/client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/youtube"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"


class YoutubeManager:
    def __init__(self, token_path=None):
        self.youtube = self.get_authenticated_service(token_path)

    def get_authenticated_service(self, token_path):
        if not token_path:
            token_path = "/opt/airflow/data/token.json"
        creds = None
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CLIENT_SECRETS_FILE,
                    SCOPES,
                )
                creds = flow.run_local_server(port=0)
            with open(token_path, "w") as token:
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

    def playlistItems_delete(self, id_: int):
        request = self.youtube.playlistItems().delete(id=id_)
        response = request.execute()
        return response

    def video_insert(self, file: os.PathLike, options):
        #! check if exist ?
        # tags = None
        # if options.keywords:
        #     tags = options.keywords.split(",")
        body = {
            "snippet": {
                "title": options.get("title", "no title"),
                "description": options.get("description", "no description"),
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

    def download_video(self, video_id, path):
        yt = YouTube(f"http://youtube.com/watch?v={video_id}")
        yt.streams.filter(progressive=True, file_extension="mp4").order_by(
            "resolution"
        ).asc().first().download(
            filename_prefix=f"{video_id}_", output_path=path, max_retries=10, timeout=10
        )

    def download_thumbnail(self, url, path, name):
        with open(f"{os.path.join(path, name)}.jpg", "wb") as f:
            f.write(requests.get(url, timeout=5).content)


def main():
    load_dotenv(find_dotenv())
    yt_manager = YoutubeManager()


if __name__ == "__main__":
    main()
