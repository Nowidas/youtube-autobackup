### Recreate already misssing files (init backup)

to_do (how to choose which playlist to follow)

### Backuping updated tracks in playlist

Some brainstormed funtions:

```python
def insert_video_in(place_num: int, video_id: str, playlist_id: str):
    ''' Inser given video (by id???) on given place in chosed playlist'''
```

```python
def upload_video(path_to_vide):
    ''' Upload video to youtube, returns video_id '''
    return video_id
```

#### Pipline (by case)

- **Video is added** (check on each day)

  Check current saved videos (as list of ids/names) and mark diff as added-> download added list

  ( how to preserve ORDER -> by counting form beginning? )

- **Video is deleted**

  Check for KEY_WORD name (like 'deleted video', 'private') -> Get saved file (by id? depends on which info is preserved for deleted video) -> upload deleted video (as private) -> (optional: check if all users have rights to watch that video) -> insert video in place of deleted + delete deleted entry from playlist (? what if video were restored?)

#### Reserch already existing solution <in_progress>

#### Quotas

free qouata: 10_000/day

every day:

- list all playlists = playlist*num * tracks*on (7 * 500 = 3_500) => 1pt / 50 tracks => 70pt / day
  if track added (1/day):
- download wideo = https://github.com/pytube/pytube (no pt xD)
  if track deleted (1/week):
- upload video = 1600pt
- change position = 50pt

( deleted and after undeleted -> what then )

### Airflow / Crone tasks:

- refresh token (send mail if token somehow expires)
- check for new videos -> new video = no in 'downloaded metadata list' -> download video + update metadata file
- check for deleted videos -> deleted video = video not accessible -> replace deleted video with local video
