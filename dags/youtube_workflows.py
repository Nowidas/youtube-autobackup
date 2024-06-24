import datetime
import logging
import os
import glob
import json
import pandas as pd
from dotenv import load_dotenv, find_dotenv

from pytube import YouTube
from pytube.exceptions import VideoUnavailable

from youtube_manager import YoutubeManager, _default_clients
from helpers import check_unlisted, get_max_thumbnail


load_dotenv(find_dotenv())
yt_manager = YoutubeManager()


def pandas_load() -> pd.DataFrame:
    all_videos = {}
    all_playlists = yt_manager.playlist_list(os.getenv("USER_ID"))

    for playlist in all_playlists:
        playlist_id = playlist["id"]
        playlist_vids = yt_manager.playlist_elements(playlist_id)
        all_videos[playlist_id] = playlist_vids

    df = pd.DataFrame()
    for playlist_id, playlist_vids in all_videos.items():
        batch = pd.json_normalize(playlist_vids)
        batch["playlist_id"] = playlist_id
        df = pd.concat([df, batch])
    return df


def update_manifest(resp_df: pd.DataFrame) -> None:
    loaded_h5 = pd.read_hdf(
        os.path.join(os.getenv("DATA_PATH"), "manifest.h5"), key="df"
    )
    new_added = resp_df.drop_duplicates(subset="contentDetails.videoId").copy()
    new_added = new_added[
        ~new_added["contentDetails.videoId"].isin(loaded_h5["contentDetails.videoId"])
    ]
    new_added["fetch_date"] = str(pd.Timestamp.now())
    new_added = new_added.reset_index(drop=True)

    new_added = new_added[
        new_added["snippet.videoOwnerChannelId"] != os.getenv("USER_ID")
    ]
    print(f"New videos: {len(new_added)}")
    loaded_h5 = pd.concat([loaded_h5, new_added])
    loaded_h5.to_hdf(
        os.path.join(os.getenv("DATA_PATH"), "manifest.h5"), key="df", mode="w"
    )


def download_new():
    loaded_h5 = pd.read_hdf(
        os.path.join(os.getenv("DATA_PATH"), "manifest.h5"), key="df"
    )
    loaded_h5 = loaded_h5.reset_index(drop=True)
    DOWNLOADED_STATUS = ["Downloaded"]
    NOT_VALID_STATUS = [
        " is unavailable",
        " is a private video",
        "Remote end closed connection without response",
        "IncompleteRead",
        "streamingData",
        " is age restricted, and can't be accessed without logging in.",
    ]  #
    new_added = loaded_h5[
        ~loaded_h5["backup_status"].str.contains(
            "|".join(NOT_VALID_STATUS + DOWNLOADED_STATUS), na=False
        )
    ]
    broken = loaded_h5[
        loaded_h5["backup_status"].str.contains("|".join(NOT_VALID_STATUS), na=False)
    ]
    print(
        f"For backup: {len(new_added)}, Broken: {len(broken)} Total: {len(loaded_h5)}"
    )
    # download new videos
    for enum, (idx, row) in enumerate(new_added.iterrows()):
        backup_path = os.path.join(os.getenv("DATA_PATH"), row["playlist_id"])
        if not os.path.exists(backup_path):
            os.makedirs(backup_path)

        thumbnail_path = os.path.join(os.getenv("DATA_PATH"), "thumbnails")
        if not os.path.exists(thumbnail_path):
            os.makedirs(thumbnail_path)

        _break = False
        for client in ["ANDROID_EMBED"] + list(_default_clients.keys()):
            if _break:
                break
            _default_clients["ANDROID_MUSIC"] = _default_clients[client]
            try:
                msg = ""
                yt_manager.download_video(
                    row["contentDetails.videoId"], path=backup_path
                )
                msg = f"Downloaded_{client} {row['contentDetails.videoId']}"
                _break = True
            except KeyboardInterrupt:
                loaded_h5.loc[idx, "backup_status"] = msg
                loaded_h5.to_hdf(
                    os.path.join(os.getenv("DATA_PATH"), "manifest.h5"),
                    key="df",
                    mode="w",
                )
                raise KeyboardInterrupt
            except Exception as e:
                msg += (
                    f"Error downloading {client}:{row['contentDetails.videoId']}: {e}, "
                )
            finally:
                loaded_h5.loc[idx, "backup_status"] = msg
                print(f"({enum+1}/{len(new_added)}) {msg}")

        # download thumbnails
        try:
            yt_manager.download_thumbnail(
                get_max_thumbnail(row),
                path=thumbnail_path,
                name=row["contentDetails.videoId"],
            )
        except Exception as e:
            print(
                f"Error downloading thumbnail for {row['contentDetails.videoId']}: {e}"
            )

    loaded_h5.to_hdf(
        os.path.join(os.getenv("DATA_PATH"), "manifest.h5"), key="df", mode="w"
    )


def import_manifest():
    loaded_h5 = pd.read_hdf(
        os.path.join(os.getenv("DATA_PATH"), "manifest.h5"), key="df"
    )
    loaded_h5.to_csv("FULLALL_tracks.csv")


def upload_backup(resp_df: pd.DataFrame):
    backup_metadata = pd.read_hdf(
        os.path.join(os.getenv("DATA_PATH"), "manifest.h5"), key="df"
    )
    backup_metadata = (
        backup_metadata.reset_index(drop=True).rename_axis("iter").reset_index()
    )

    deleted = resp_df[
        (
            resp_df["snippet.title"].isin(
                ["Deleted video", "Private video", "This video is unavailable."]
            )
        )
        | (resp_df["status.privacyStatus"].isin(["unlisted"]))
    ].copy()
    deleted = deleted.loc[
        deleted["snippet.videoOwnerChannelId"] != os.getenv("USER_ID")
    ]
    deleted = deleted[
        [
            "contentDetails.videoId",
            "snippet.position",
            "playlist_id",
            "id",
            "status.privacyStatus",
        ]
    ].rename(
        columns={
            "snippet.position": "api.snippet.position",
            "playlist_id": "api.playlist_id",
            "id": "api.id",
            "status.privacyStatus": "api.status.privacyStatus",
        }
    )
    deleted = deleted[deleted.apply(check_unlisted, axis=1)]

    deleted = pd.merge(
        deleted, backup_metadata, on="contentDetails.videoId", how="left"
    )
    deleted = deleted.set_index("iter")
    backup_metadata = backup_metadata.drop(columns=["iter"])

    max_dayly_upload = 4
    for enum, (idx, row) in enumerate(deleted.iterrows()):

        if "Downloaded" not in str(row["backup_status"]):
            print(
                f"({enum+1}/{len(deleted)}) Can not revive {row['contentDetails.videoId']} in {row['api.playlist_id']} on position {row['api.snippet.position']} - missing backup"
            )
            # yt_manager.playlistItems_insert(row['api.playlist_id'], 'KWkXqsVu1Eo', position=row['api.snippet.position'])
            # yt_manager.playlistItems_delete(row['api.id'])
            continue

        backup_folder = os.path.join(os.getenv("DATA_PATH"), "*")
        backup_file = glob.glob(
            os.path.join(backup_folder, f"{row['contentDetails.videoId']}*")
        )[0]
        options = {
            "title": row["snippet.title"],
            "description": f"""
BACKUP OF {row['contentDetails.videoId']}

======== RIGINAL CHANNEL ==================
{row['snippet.videoOwnerChannelTitle']} ({row['snippet.videoOwnerChannelId']})

======= ORIGINAL PUBLISHED DATE ===========
{row['contentDetails.videoPublishedAt']}

======= DESCRIPTION =======================
{row['snippet.description']}

======= COMMENTS ==========================
work in progress
            """,
        }
        # check existing backaped video
        all_matched_id = backup_metadata[
            (backup_metadata["contentDetails.videoId"] == row["contentDetails.videoId"])
            & (backup_metadata["retrieve_status"].str.contains("Uploaded", na=False))
            | (backup_metadata["retrieve_status"].str.contains("Existed", na=False))
        ]["retrieve_status"]

        print(f"{options=}")
        print(f"{all_matched_id=}")
        # continue  #!DEBUG

        try:
            if len(all_matched_id) > 0:
                new_video_id = (
                    all_matched_id.iloc[0]
                    .replace("Uploaded ", "")
                    .replace("Existed ", "")
                )
            else:
                if max_dayly_upload == 0:
                    logging.warning("Max dayly upload reached")
                max_dayly_upload -= 1
                new_video_id = yt_manager.video_insert(backup_file, options)
            yt_manager.playlistItems_insert(
                row["api.playlist_id"],
                new_video_id,
                position=row["api.snippet.position"],
            )
            yt_manager.playlistItems_delete(row["api.id"])
            msg = f"Uploaded {new_video_id}"
        except KeyboardInterrupt:
            backup_metadata.loc[idx, "retrieve_status"] = msg
            backup_metadata.to_hdf(
                os.path.join(os.getenv("DATA_PATH"), "manifest.h5"), key="df", mode="w"
            )
            raise KeyboardInterrupt
        except Exception as e:
            msg = f"Error {row['contentDetails.videoId']}: {e}"
            backup_metadata.loc[idx, "retrieve_status"] = msg
        finally:
            backup_metadata.loc[idx, "retrieve_status"] = msg
            print(f"({enum+1}/{len(backup_metadata)}) {msg}")

    backup_metadata.to_hdf(
        os.path.join(os.getenv("DATA_PATH"), "manifest.h5"), key="df", mode="w"
    )


def restore_uploaded(resp_df):
    backup_metadata = pd.read_hdf(
        os.path.join(os.getenv("DATA_PATH"), "manifest.h5"), key="df"
    )
    backup_metadata = backup_metadata.reset_index(drop=True)
    retrieved = backup_metadata[
        (backup_metadata["retrieve_status"].str.contains("Uploaded", na=False))
    ]
    print(f"Uploaded videos: {len(retrieved)} checking if they are back to live...")
    # check if video is back to live
    for enum, (idx, row) in enumerate(retrieved.iterrows()):
        backup_id = row["retrieve_status"].replace("Uploaded ", "")
        try:
            yt = YouTube(
                f"http://youtube.com/watch?v={row['contentDetails.videoId']}"
            ).streams
        except VideoUnavailable as e:
            continue
        else:
            msg = f"Video {row['contentDetails.videoId']} is back to live, replacing... {backup_id} -> {row['contentDetails.videoId']}"
            print(f"({enum+1}/{len(retrieved)}) {msg}")
            filtered_resp = resp_df[
                resp_df["contentDetails.videoId"] == row["contentDetails.videoId"]
            ]
            for _, row in filtered_resp.iterrows():
                yt_manager.playlistItems_insert(
                    row["playlist_id"],
                    row["contentDetails.videoId"],
                    position=row["snippet.position"],
                )
                yt_manager.playlistItems_delete(row["api.id"])
                print(
                    f"Replaced {row['contentDetails.videoId']} in {row['playlist_id']}"
                )
            backup_metadata.loc[idx, "retrieve_status"] = (
                f"Existed {row['contentDetails.videoId']}"
            )


def backup_metadata():
    BACKUP_PATH = os.getenv("DATA_PATH")
    if not os.path.exists(BACKUP_PATH):
        os.makedirs(BACKUP_PATH)
    backup_full = os.path.join(
        BACKUP_PATH,
        "backup",
        f"manifest_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.h5",
    )
    backup_metadata = pd.read_hdf(
        os.path.join(os.getenv("DATA_PATH"), "manifest.h5"), key="df"
    )
    backup_metadata.to_hdf(backup_full, key="df", mode="w")
    print(f"Backup saved to {backup_full}")


def restore_token():
    _ = YoutubeManager()
    print("Token restored")
