import re
import pandas as pd
from pytube import YouTube
from pytube.exceptions import VideoUnavailable


def get_max_thumbnail(row: pd.Series) -> str:
    pattern_url = re.compile(r"snippet\.thumbnails\..*\.url", flags=re.IGNORECASE)
    url_cols = [col for col in row.index if re.search(pattern_url, col)]
    urls = row[url_cols].dropna()
    return urls.iloc[-1]


def check_unlisted(row: pd.Series) -> bool:
    if row["api.status.privacyStatus"] == "unlisted":
        try:
            yt = YouTube(
                f"http://youtube.com/watch?v={row['contentDetails.videoId']}"
            ).streams
        except VideoUnavailable:
            return True
        else:
            return False
    return True
