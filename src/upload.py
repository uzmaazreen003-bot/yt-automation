"""YouTube Data API v3 upload (resumable), thumbnail, first comment."""
import os
import time

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]


def service():
    creds = Credentials(
        None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload(video_path, title, description, tags, cfg, thumb_path=None, comment=None):
    yt = service()
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": tags,
            "categoryId": str(cfg.get("category_id", "27")),
            "defaultLanguage": cfg.get("language", "hi"),
            "defaultAudioLanguage": cfg.get("language", "hi"),
        },
        "status": {
            "privacyStatus": cfg.get("privacy", "public"),
            "selfDeclaredMadeForKids": bool(cfg.get("made_for_kids", False)),
            "containsSyntheticMedia": bool(cfg.get("synthetic_disclosure", True)),
        },
    }
    media = MediaFileUpload(video_path, mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp, tries = None, 0
    while resp is None:
        try:
            status, resp = req.next_chunk()
            if status:
                print(f"  uploaded {int(status.progress() * 100)}%", flush=True)
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and tries < 8:
                tries += 1
                time.sleep(2 ** tries)
                continue
            raise
        except (ConnectionError, TimeoutError, OSError) as e:
            if tries < 8:
                tries += 1
                print("  upload hiccup, retrying:", e)
                time.sleep(2 ** tries)
                continue
            raise
    vid = resp["id"]
    print("  video id:", vid)

    if thumb_path and os.path.exists(thumb_path):
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(thumb_path, mimetype="image/png")).execute()
        except HttpError as e:
            print("  thumbnail not set (channel may need phone verification):", str(e)[:200])
    if comment:
        try:
            yt.commentThreads().insert(part="snippet", body={"snippet": {"videoId": vid, "topLevelComment": {
                "snippet": {"textOriginal": comment}}}}).execute()
        except HttpError as e:
            print("  comment not posted:", str(e)[:200])
    return vid
