import argparse
import json
import os
import uuid
from datetime import date, datetime
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
APP_ID = '85bfa892-43b6-40ec-8f07-255f95f6fd43'
BASE = 'https://ebenezeraghouston.github.io/ebenezer-church-app/#events'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--date', type=date.fromisoformat)
    args = parser.parse_args()
    if args.date and not args.dry_run:
        parser.error('--date requires --dry-run')
    now = datetime.now(ZoneInfo('America/Chicago'))
    today = args.date or now.date()
    events = json.loads((ROOT / 'events.json').read_text(encoding='utf-8'))
    key = os.environ.get('ONESIGNAL_REST_API_KEY')
    if not args.dry_run and not key:
        raise SystemExit('Missing secret ONESIGNAL_REST_API_KEY')
    count = 0
    for event in events:
        start = date.fromisoformat(event['date'])
        days = (start - today).days
        if days not in (0, 1) or event.get('reminders') is False:
            continue
        if days == 0 and not args.dry_run and event.get('start_local'):
            if now.replace(tzinfo=None) >= datetime.fromisoformat(event['start_local']):
                continue
        label = 'Tomorrow' if days == 1 else 'Today'
        event_id = event.get('id', event['title'] + event['date'])
        token = uuid.uuid3(uuid.NAMESPACE_URL, f'{APP_ID}/{event_id}/{start}/{days}')
        payload = {'app_id': APP_ID, 'included_segments': ['Subscribed Users'], 'target_channel': 'push', 'headings': {'en': f'{label}: {event["title"]}'}, 'contents': {'en': f'{event.get("time", "Time to be announced")} · {event.get("note", "See details in church app.")}'}, 'url': BASE, 'idempotency_key': str(token), 'ttl': 3600}
        count += 1
        print(f'{label}: {event["title"]} ({start})', flush=True)
        if not args.dry_run:
            req = Request('https://api.onesignal.com/notifications', data=json.dumps(payload).encode(), headers={'Authorization': 'Key ' + key, 'Content-Type': 'application/json'}, method='POST')
            with urlopen(req, timeout=30) as resp:
                result = json.load(resp)
            if not result.get('id'):
                raise RuntimeError('OneSignal notification not accepted: ' + str(result.get('errors', 'unknown error')))
            print('OneSignal accepted notification:', result['id'])
    print(f'{today}: {count} reminder(s) {"previewed" if args.dry_run else "processed"}.')

if __name__ == '__main__':
    main()
