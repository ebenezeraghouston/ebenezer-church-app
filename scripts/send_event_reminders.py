import argparse
import json
import os
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
APP_ID = '85bfa892-43b6-40ec-8f07-255f95f6fd43'
BASE = 'https://ebenezeraghouston.github.io/ebenezer-church-app/#events'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--date', type=date.fromisoformat)
    parser.add_argument('--preview-time', help='Houston local HH:MM; dry run only')
    args = parser.parse_args()
    if (args.date or args.preview_time) and not args.dry_run:
        parser.error('--date and --preview-time require --dry-run')
    now = datetime.now(ZoneInfo('America/Chicago'))
    if args.preview_time:
        now = datetime.combine(args.date or now.date(), time.fromisoformat(args.preview_time), ZoneInfo('America/Chicago'))
    today = args.date or now.date()
    events = json.loads((ROOT / 'events.json').read_text(encoding='utf-8'))
    key = os.environ.get('ONESIGNAL_REST_API_KEY')
    if not args.dry_run and not key:
        raise SystemExit('Missing secret ONESIGNAL_REST_API_KEY')
    count = 0
    def send(title, body, token, url):
        nonlocal count
        count += 1
        print(f'{title}: {body}', flush=True)
        if args.dry_run:
            return
        payload = {'app_id': APP_ID, 'included_segments': ['Subscribed Users'], 'target_channel': 'push', 'headings': {'en': title}, 'contents': {'en': body}, 'url': url, 'idempotency_key': str(token), 'ttl': 3600}
        req = Request('https://api.onesignal.com/notifications', data=json.dumps(payload).encode(), headers={'Authorization': 'Key ' + key, 'Content-Type': 'application/json'}, method='POST')
        with urlopen(req, timeout=30) as resp:
            result = json.load(resp)
        if not result.get('id'):
            raise RuntimeError('OneSignal notification not accepted: ' + str(result.get('errors', 'unknown error')))
        print('OneSignal accepted notification:', result['id'])
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
        title = f'{label}: {event["title"]}'
        body = f'{event.get("time", "Time to be announced")} · {event.get("note", "See details in church app.")}'
        notice_url = BASE.split('#')[0] + '?' + urlencode({'notice_title': title, 'notice_body': body, 'notice_id': str(token)}) + '#notifications'
        send(title, body, token, notice_url)
    # Recurring weekly meetings are based on the published church homepage schedule.
    # Send during a 20-minute window starting 30 minutes before the meeting.
    # Idempotency keys prevent duplicate pushes from overlapping scheduled runs.
    weekly = [
        {'id':'womens-zoom-prayer','title':"Women's Zoom Prayer",'days':(0,1,2,3),'hour':14,'minute':0,'time':'2:00 PM','note':'Join the weekly Zoom prayer meeting.'},
        {'id':'friday-fasting-prayer','title':'Friday Fasting Prayer (Zoom)','days':(4,),'hour':10,'minute':0,'time':'10:00 AM','note':'Join the weekly fasting prayer on Zoom.'},
    ]
    for meeting in weekly:
        if now.weekday() not in meeting['days']:
            continue
        meeting_start = now.replace(hour=meeting['hour'],minute=meeting['minute'],second=0,microsecond=0)
        reminder_at = meeting_start - timedelta(minutes=30)
        if not (reminder_at <= now < reminder_at + timedelta(minutes=20)):
            continue
        title = 'Starting in 30 minutes: ' + meeting['title']
        body = meeting['time'] + ' Houston time · ' + meeting['note']
        token = uuid.uuid3(uuid.NAMESPACE_URL, f'{APP_ID}/{meeting["id"]}/{today}/30min')
        notice_url = BASE.split('#')[0] + '?' + urlencode({'notice_title':title,'notice_body':body,'notice_id':str(token)}) + '#notifications'
        send(title,body,token,notice_url)
    print(f'{today}: {count} reminder(s) {"previewed" if args.dry_run else "processed"}.')

if __name__ == '__main__':
    main()
