import os
import time
from http import client
import httplib2

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

CLIENT_SECRETS_FILE = 'client_secret.json'

SCOPES = ['https://www.googleapis.com/auth/youtube']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

# Authorize the request and store authorization credentials.
def get_authenticated_service():
    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, SCOPES)
    credentials = flow.run_local_server()
    return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

def all_playlist(user_id):
    pass

def get_playlist(playlist_id):
    full_list = []
    playlistItems = youtube.playlistItems()
    request = playlistItems.list(
        part="id,contentDetails,snippet,status",
        playlistId=playlist_id,
        maxResults=50,
    )
    while request is not None:
        playlist_tracks = request.execute()

        # Do something with the activities
        full_list.extend(playlist_tracks["items"])

        request = playlistItems.list_next(request, playlist_tracks)
        
    return full_list
    
youtube = get_authenticated_service()

def position_video(place_num: int, video_id: str, playlist_id: str):
    ''' Inser given video (by id???) on given place in chosed playlist'''
    request = youtube.playlistItems().update(
        part="snippet",
        body={
          "id": video_id, #"YOUR_PLAYLIST_ITEM_ID" #!!!! ????
          "snippet": {
            "playlistId": playlist_id, #"YOUR_PLAYLIST_ID",
            "position": place_num,
            "resourceId": {
              "kind": "youtube#video",
              "videoId": video_id #"YOUR_VIDEO_ID"
            }
          }
        }
    )
    response = request.execute()
    return response


httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, client.NotConnected,
                        client.IncompleteRead, client.ImproperConnectionState,
                        client.CannotSendRequest, client.CannotSendHeader,
                        client.ResponseNotReady, client.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]


def resumable_upload(request):
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            print('Uploading file...')
            status, response = request.next_chunk()
            if response is not None:
                if 'id' in response:
                    print('Video id "%s" was successfully uploaded.' %
                          response['id'])
                else:
                    exit('The upload failed with an unexpected response: %s' % response)
        except (HttpError, e):
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = 'A retriable HTTP error %d occurred:\n%s' % (e.resp.status,
                                                                     e.content)
            else:
                raise
        except (RETRIABLE_EXCEPTIONS, e):
            error = 'A retriable error occurred: %s' % e

        if error is not None:
            print(error)
            retry += 1
            if retry > MAX_RETRIES:
                exit('No longer attempting to retry.')

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            print('Sleeping %f seconds and then retrying...' % sleep_seconds)
            time.sleep(sleep_seconds)

def upload_video(path_to_video: os.PathLike, options):
    tags = None
    if options.keywords:
        tags = options.keywords.split(',')

    body = dict(
        snippet=dict(
            title=options.title,
            description=options.description,
            tags=tags,
            categoryId=options.category
        ),
        status=dict(
            privacyStatus=options.privacyStatus
        )
    )

    # Call the API's videos.insert method to create and upload the video.
    insert_request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True)
    )

    resumable_upload(insert_request)


from pytube import YouTube

def download_video(video_id):
    yt = YouTube(f'http://youtube.com/watch?v={video_id}')
    yt.streams \
        .order_by('resolution') \
        .desc() \
        .first() \
        .download() \


