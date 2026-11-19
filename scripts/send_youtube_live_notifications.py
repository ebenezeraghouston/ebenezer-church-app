"""Notify subscribed church app members once per active YouTube livestream."""
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "youtube-live-state.json"
APP_ID = "85bfa892-43b6-40ec-8f07-255f95f6fd43"
CHANNEL_HANDLE = "ebenezeraghtx"
API_ROOT = "https://www.googleapis.com/youtube/v3/"

def get_json(url, headers=None):
    with urlopen(Request(url, headers=headers or {}), timeout=25) as response:
        return json.load(response)

def youtube(api_key, endpoint, **params):
    return get_json(API_ROOT + endpoint + "?" + urlencode({**params, "key": api_key}))

def main():
    api_key = os.environ.get("YOUTUBE_API_KEY")
    onesignal_key = os.environ.get("ONESIGNAL_REST_API_KEY")
    if not api_key or not onesignal_key:
        raise SystemExit("Configure YOUTUBE_API_KEY and ONESIGNAL_REST_API_KEY as GitHub Actions secrets.")
    channels = youtube(api_key, "channels", part="id", forHandle=CHANNEL_HANDLE)
    items = channels.get("items", [])
    if not items:
        raise SystemExit("Could not resolve the official YouTube channel handle.")
    channel_id = items[0]["id"]
    results = youtube(api_key, "search", part="snippet", channelId=channel_id,
                      eventType="live", type="video", maxResults=10)
    videos = [item["id"]["videoId"] for item in results.get("items", []) if item.get("id", {}).get("videoId")]
    if not videos:
        print("No live broadcast detected.")
        return
    details = youtube(api_key, "videos", part="snippet,liveStreamingDetails", id=",".join(videos))
    live = [v for v in details.get("items", []) if v.get("snippet", {}).get("liveBroadcastContent") == "live"
            and v.get("liveStreamingDetails", {}).get("actualStartTime")
            and not v.get("liveStreamingDetails", {}).get("actualEndTime")]
    if not live:
        print("No active livestream detected.")
        return
    state = json.loads(STATE.read_text()) if STATE.exists() else {"notified_video_ids": []}
    seen = state.get("notified_video_ids", [])
    for video in live:
        vid = video["id"]
        if vid in seen:
            print("Already notified for livestream", vid)
            continue
        title = video["snippet"]["title"]
        url = "https://www.youtube.com/watch?v=" + vid
        payload = {
            "app_id": APP_ID,
            "included_segments": ["Total Subscriptions"],
            "target_channel": "push",
            "headings": {"en": "🔴 Ebenezer AG is LIVE!"},
            "contents": {"en": "Join our livestream: " + title[:110]},
            "url": url,
            "idempotency_key": str(uuid.uuid5(uuid.NAMESPACE_URL, APP_ID + "/youtube/" + vid)),
            "ttl": 3600
        }
        request = Request("https://api.onesignal.com/notifications",
                          data=json.dumps(payload).encode("utf-8"),
                          headers={"Authorization": "Key " + onesignal_key, "Content-Type": "application/json"},
                          method="POST")
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
        if not result.get("id"):
            raise RuntimeError("OneSignal did not accept the notification: " + str(result.get("errors")))
        seen.append(vid)
        print("Sent livestream notification for", vid)
    state["notified_video_ids"] = seen[-200:]
    state["last_checked_utc"] = datetime.now(timezone.utc).isoformat()
    STATE.write_text(json.dumps(state, indent=2) + "\n")

if __name__ == "__main__":
    main()
