#!/usr/bin/env python3
"""Process pending church admin announcements using GitHub Actions secrets."""
import json, os, sys, urllib.request, urllib.error
from datetime import datetime, timezone
from google.cloud import firestore
from google.oauth2 import service_account

PROJECT = "ebenezer-ag-church-app"
APP_ID = "85bfa892-43b6-40ec-8f07-255f95f6fd43"
URL = "https://ebenezeraghouston.github.io/ebenezer-church-app/#notifications"

def main():
    raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "")
    key = os.environ.get("ONESIGNAL_REST_API_KEY", "")
    if not raw or not key:
        raise SystemExit("Missing FIREBASE_SERVICE_ACCOUNT_JSON or ONESIGNAL_REST_API_KEY GitHub Actions secret")
    credentials = service_account.Credentials.from_service_account_info(json.loads(raw))
    db = firestore.Client(project=PROJECT, credentials=credentials)
    pending = db.collection("adminAnnouncements").where("status", "==", "pending").limit(25).stream()
    count = 0
    for snapshot in pending:
        ref = snapshot.reference
        @firestore.transactional
        def claim(transaction):
            current = ref.get(transaction=transaction)
            if not current.exists or current.get("status") != "pending":
                return False
            transaction.update(ref, {"status": "sending", "processingAt": firestore.SERVER_TIMESTAMP})
            return True
        if not claim(db.transaction()):
            continue
        data = snapshot.to_dict()
        body = {
            "app_id": APP_ID, "target_channel": "push",
            "included_segments": ["Subscribed Users"],
            "headings": {"en": data["title"]},
            "contents": {"en": data["message"]},
            "url": URL,
        }
        request = urllib.request.Request(
            "https://api.onesignal.com/notifications",
            data=json.dumps(body).encode(),
            headers={"Authorization": "Key " + key, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                result = json.load(response)
            if not result.get("id"):
                raise RuntimeError("OneSignal did not return a notification ID: " + str(result)[:300])
            ref.update({
                "status": "sent", "sentAt": firestore.SERVER_TIMESTAMP,
                "onesignalId": result["id"], "recipients": result.get("recipients"),
            })
            print("Accepted by OneSignal:", snapshot.id)
        except Exception as exc:
            # Do not auto-retry ambiguous failures: prevents accidental duplicate sends.
            ref.update({"status": "failed", "failedAt": firestore.SERVER_TIMESTAMP, "errorMessage": str(exc)[:400]})
            print("Failed:", snapshot.id, str(exc)[:200], file=sys.stderr)
        count += 1
    print("Processed", count, "queued announcement(s)")

if __name__ == "__main__":
    main()
