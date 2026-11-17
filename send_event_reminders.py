#!/usr/bin/env python3
"""Send opted-in OneSignal subscribers day-before and day-of event reminders.

Run hourly via GitHub Actions. Sends at ~9 AM Houston time. Maintains a small
non-personal send ledger in reminder-state.json. Does not send on dry-run.
"""
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

BASE = pathlib.Path(__file__).resolve().parents[1]
STATE = BASE / 'reminder-state.json'
APP_URL = 'https://ebenezeraghouston.github.io/ebenezer-church-app/'
TZ = ZoneInfo('America/Chicago')

def main():
    now = dt.datetime.now(TZ)
    dry_run = os.environ.get('DRY_RUN', '').lower() == 'true'
    force = os.environ.get('FORCE_CHECK', '').lower() == 'true'
    print('Houston local time:', now.isoformat(), '| dry run:', dry_run)
    if not force and now.hour != 9:
        print('Outside the 9 AM Houston reminder window. No sends.')
        return 0
    events = json.loads((BASE / 'events.json').read_text(encoding='utf-8'))
    ledger = json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {'sent': []}
    sent = set(ledger.get('sent', []))
    app_id = os.environ.get('ONESIGNAL_APP_ID', '').strip()
    api_key = os.environ.get('ONESIGNAL_REST_API_KEY', '').strip()
    if not dry_run and (not app_id or not api_key):
        print('Missing ONESIGNAL_APP_ID or ONESIGNAL_REST_API_KEY. No sends.', file=sys.stderr)
        return 1
    errors = 0
    for event in events:
        if not isinstance(event, dict) or not event.get('date') or not event.get('title'):
            continue
        start = dt.date.fromisoformat(event['date'])
        end = dt.date.fromisoformat(event.get('end', event['date']))
        # Multi-day events: reminder on day before first day, and on first day.
        # Avoid a daily barrage throughout a multi-day event.
        for kind, when in [('day_before', start - dt.timedelta(days=1)), ('day_of', start)]:
            if now.date() != when:
                continue
            key = f"{event.get('id',event['title'])}:{kind}:{when.isoformat()}"
            if key in sent:
                print('Already sent:', key)
                continue
            label = 'Tomorrow' if kind == 'day_before' else 'Today'
            time = event.get('time', 'Time to be announced')
            message = f"{event['title']} — {label.lower()}! {time}. Tap to see event details."
            print('Due:', key, '|', message)
            if dry_run:
                continue
            # OneSignal supports idempotency_key to prevent duplicate sends on retries.
            import uuid
            payload = {
                'app_id': app_id,
                'included_segments': ['Subscribed Users'],
                'headings': {'en': f'{label}: {event["title"]}'},
                'contents': {'en': message},
                'url': APP_URL + '#events',
                'idempotency_key': str(uuid.uuid5(uuid.NAMESPACE_URL, APP_URL + key)),
            }
            req = urllib.request.Request(
                'https://api.onesignal.com/notifications',
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json', 'Authorization': 'Key ' + api_key},
                method='POST',
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.load(resp)
                    if not result.get('id'):
                        raise RuntimeError('OneSignal response has no notification id: ' + str(result)[:300])
                    print('OneSignal accepted:', result['id'])
                    sent.add(key)
                    STATE.write_text(json.dumps({'sent': sorted(sent)}, indent=2) + '\n', encoding='utf-8')
            except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError) as ex:
                errors += 1
                print('ERROR:', key, str(ex), file=sys.stderr)
    if not errors:
        print('Finished; no errors. Reminders due only on event start date and previous date.')
    return 1 if errors else 0

if __name__ == '__main__':
    sys.exit(main())
