### Recreate already misssing files (init backup)

to_do (how to choose which playlist to follow)

### Buckuping updated tracks in playlist

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
  
  Check current saved viedos (as list of ids/names) and mark diff as added-> download added list
  
  ( how to preserve ORDER -> by counting form beginnig? )

- **Video is deleted**
  
  Check for KEY_WORD name (like 'deleted video', 'private') -> Get saved file (by id? depedns on which info is preserved for deleted video) -> upload deleted video (as private) -> (optional: check if all users have rights to watch that video) -> insert video in place of deleted + delete deleted entry from playlist (? what if video were restored?)

#### Reserch already existing solution <in_progress>
