"""Notify subscribers once when Ebenezer AG's YouTube channel goes live."""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SEED_VIDEO = "https://www.youtube.com/watch?v=8AqrHrYCiv8"
APP_ID = "85bfa892-43b6-40ec-8f07-255f95f6fd43"
STATE = ROOT / "youtube_live_state.json"

def main():
    import yt_dlp
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    opts = {"quiet": True, "no_warnings": True, "skip_download": True,
            "extract_flat": False, "ignoreerrors": False, "socket_timeout": 20}
    channel_id = state.get("channel_id")
    if not channel_id:
        with yt_dlp.YoutubeDL(opts) as ydl:
            video = ydl.extract_info(SEED_VIDEO, download=False)
        channel_id = video.get("channel_id")
        if not channel_id:
            raise RuntimeError("Could not resolve YouTube channel from the supplied livestream")
        state["channel_id"] = channel_id
        print("Resolved channel:", channel_id)
    # /live resolves to the channel's current livestream, if one is active.
    with yt_dlp.YoutubeDL(opts) as ydl:
        live = ydl.extract_info(f"https://www.youtube.com/channel/{channel_id}/live", download=False)
    if not live or live.get("live_status") != "is_live":
        print("Channel is not currently live. No push sent.")
        STATE.write_text(json.dumps(state, indent=2) + "\n")
        return
    video_id = live.get("id")
    if not video_id:
        raise RuntimeError("Live video has no ID")
    if video_id in state.get("notified_video_ids", []):
        print("Already notified for livestream:", video_id)
        return
    title = "Ebenezer AG is LIVE on YouTube!"
    body = "Our church livestream is happening now. Tap to watch: " + live.get("title", "Sunday Worship")
    url = "https://www.youtube.com/watch?v=" + video_id
    key = os.environ.get("ONESIGNAL_REST_API_KEY")
    if not key:
        raise RuntimeError("Missing ONESIGNAL_REST_API_KEY")
    payload = {"app_id": APP_ID, "included_segments": ["Total Subscriptions"],
               "target_channel": "push", "headings": {"en": title},
               "contents": {"en": body}, "url": url, "ttl": 3600,
               "idempotency_key": str(uuid.uuid5(uuid.NAMESPACE_URL, APP_ID + "/youtube-live/" + video_id))}
    req = Request("https://api.onesignal.com/notifications",
                  data=json.dumps(payload).encode(),
                  headers={"Authorization": "Key " + key, "Content-Type": "application/json"},
                  method="POST")
    with urlopen(req, timeout=30) as response:
        result = json.load(response)
    if not result.get("id"):
        raise RuntimeError("OneSignal did not accept the livestream notification: " + str(result))
    print("OneSignal accepted live push:", result["id"], url)
    state["notified_video_ids"] = (state.get("notified_video_ids", []) + [video_id])[-100:]
    state["last_notification_at"] = datetime.now(timezone.utc).isoformat()
    STATE.write_text(json.dumps(state, indent=2) + "\n")

if __name__ == "__main__":
    main()
