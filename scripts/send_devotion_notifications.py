#!/usr/bin/env python3
"""Send one push notification for each newly published church devotion.

Requires existing GitHub secrets FIREBASE_SERVICE_ACCOUNT_JSON and
ONESIGNAL_REST_API_KEY. Firestore receipts, not repository commits, prevent
repeated sends. The first live run establishes a baseline without notifying
subscribers about old devotions.
"""
import argparse
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import firebase_admin
from firebase_admin import credentials, firestore

APP_ID = "85bfa892-43b6-40ec-8f07-255f95f6fd43"
APP_URL = "https://ebenezeraghouston.github.io/ebenezer-church-app/#devotions"
STATE_PATH = "automationState/devotionNotifications"
RECEIPTS = "devotionNotificationReceipts"
MAX_AGE = timedelta(hours=48)
RETRY_PAUSE = timedelta(minutes=10)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    key = os.environ.get("ONESIGNAL_REST_API_KEY")
    if not raw:
        raise SystemExit("Missing FIREBASE_SERVICE_ACCOUNT_JSON GitHub secret")
    if not args.dry_run and not key:
        raise SystemExit("Missing ONESIGNAL_REST_API_KEY GitHub secret")

    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(json.loads(raw)))
    db = firestore.client()
    now = datetime.now(timezone.utc)

    state_ref = db.document(STATE_PATH)
    state = state_ref.get()
    if not state.exists:
        if args.dry_run:
            print("No baseline yet. First live run will initialize the baseline, without sending old devotions.")
            return
        try:
            state_ref.create({"startedAt": now, "purpose": "New devotions only; exclude existing publications"})
        except Exception:
            if not state_ref.get().exists:
                raise
        print("Devotion notification baseline initialized. Existing devotions will not be announced.")
        return

    started_at = state.to_dict().get("startedAt")
    if not isinstance(started_at, datetime):
        raise SystemExit("Devotion notification baseline has an invalid startedAt timestamp.")
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)

    pending = []
    for item in db.collection("devotions").where("status", "==", "published").stream():
        data = item.to_dict() or {}
        published_at = data.get("publishedAt")
        if not isinstance(published_at, datetime):
            continue
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        if not (started_at < published_at <= now):
            continue
        if now - published_at > MAX_AGE:
            continue
        pending.append((published_at, item.id, data))
    pending.sort(key=lambda item: item[0])
    print("Recently published devotions to check:", len(pending))

    accepted = 0
    for _, devotion_id, data in pending[:25]:
        receipt_ref = db.collection(RECEIPTS).document(devotion_id)
        receipt = receipt_ref.get()
        previous = receipt.to_dict() if receipt.exists else {}
        if previous.get("status") == "sent":
            continue

        attempted_at = previous.get("attemptedAt")
        if previous.get("status") == "sending" and isinstance(attempted_at, datetime):
            if now - attempted_at < RETRY_PAUSE:
                print("Send already in progress; skipping:", devotion_id)
                continue

        title = str(data.get("title", "")).strip()
        scripture = str(data.get("scripture", "")).strip()
        if not title:
            print("Skipping devotion with no title:", devotion_id)
            continue

        heading = ("New Devotion: " + title)[:110]
        body_text = (scripture + " - " if scripture else "") + "A new devotion is available. Tap to read it in the church app."
        body_text = body_text[:250]
        token = str(uuid.uuid5(uuid.NAMESPACE_URL, APP_ID + "/new-devotion/" + devotion_id))
        if args.dry_run:
            print("DRY RUN:", devotion_id, heading, body_text)
            continue

        attempts = int(previous.get("attempts") or 0) + 1
        receipt_ref.set({
            "status": "sending",
            "attemptedAt": now,
            "attempts": attempts,
            "publishedAt": data.get("publishedAt"),
        }, merge=True)
        payload = {
            "app_id": APP_ID,
            "target_channel": "push",
            "included_segments": ["Total Subscriptions"],
            "headings": {"en": heading},
            "contents": {"en": body_text},
            "url": APP_URL,
            "idempotency_key": token,
            "ttl": 86400,
        }
        request = Request(
            "https://api.onesignal.com/notifications",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": "Key " + key, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                result = json.load(response)
            push_id = result.get("id")
            if not push_id:
                raise RuntimeError("OneSignal did not accept notification: " + str(result.get("errors", result))[:250])
            receipt_ref.set({
                "status": "sent",
                "sentAt": firestore.SERVER_TIMESTAMP,
                "oneSignalId": push_id,
                "idempotencyKey": token,
                "error": firestore.DELETE_FIELD,
            }, merge=True)
            accepted += 1
            print("OneSignal accepted new devotion:", devotion_id, push_id, flush=True)
        except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
            receipt_ref.set({
                "status": "retry",
                "error": str(exc)[:400],
                "failedAt": firestore.SERVER_TIMESTAMP,
            }, merge=True)
            print("Devotion push not confirmed; will retry:", devotion_id, str(exc)[:180], flush=True)

    print("New devotion pushes accepted by OneSignal:", accepted)


if __name__ == "__main__":
    main()
