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
    history_path = ROOT / 'notifications.json'
    history = json.loads(history_path.read_text(encoding='utf-8'))
    original_count = len(history)
    history = [item for item in history if item.get('sent_at') and timedelta(0) <= now - datetime.fromisoformat(item['sent_at']) < timedelta(days=14)]
    history_changed = len(history) != original_count and not args.dry_run
    def send(title, body, token, url):
        nonlocal count, history_changed
        count += 1
        print(f'{title}: {body}', flush=True)
        if args.dry_run:
            return
        if any(item.get('id') == str(token) for item in history):
            print('Already sent; skipping duplicate:', token)
            return
        payload = {'app_id': APP_ID, 'included_segments': ['Subscribed Users'], 'target_channel': 'push', 'headings': {'en': title}, 'contents': {'en': body}, 'url': url, 'idempotency_key': str(token), 'ttl': 3600}
        req = Request('https://api.onesignal.com/notifications', data=json.dumps(payload).encode(), headers={'Authorization': 'Key ' + key, 'Content-Type': 'application/json'}, method='POST')
        with urlopen(req, timeout=30) as resp:
            result = json.load(resp)
        if not result.get('id'):
            raise RuntimeError('OneSignal notification not accepted: ' + str(result.get('errors', 'unknown error')))
        print('OneSignal accepted notification:', result['id'])
        if not any(item.get('id') == str(token) for item in history):
            history.insert(0, {'id':str(token), 'title':title, 'body':body, 'sent_at':now.isoformat(), 'push_id':result['id']})
            history_changed = True
    # Exact-time events: previous day (24h), 1h, and 30min before.
    # No precise reminder is sent when the event has no confirmed start_local.
    for event in events:
        if event.get('reminders') is False:
            continue
        start_times = event.get('start_times_local') or ([event['start_local']] if event.get('start_local') else [])
        for start_text in start_times:
            event_start = datetime.fromisoformat(start_text).replace(tzinfo=ZoneInfo('America/Chicago'))
            for minutes in event.get('reminder_minutes', [1440, 60, 30]):
                label = {1440: 'Tomorrow', 60: 'Starting in 1 hour', 30: 'Starting in 30 minutes'}.get(minutes, f'Starting in {minutes} minutes')
                reminder_at = event_start - timedelta(minutes=minutes)
                if not (reminder_at <= now < reminder_at + timedelta(minutes=20)):
                    continue
                event_id = event.get('id', event['title'] + event['date'])
                token = uuid.uuid3(uuid.NAMESPACE_URL, f'{APP_ID}/{event_id}/{event_start.isoformat()}/{minutes}min')
                title = label + ': ' + event['title']
                body = event_start.strftime('%a, %b %-d at %-I:%M %p') + ' Houston time · ' + event.get('note', 'See details in church app.')
                notice_url = BASE.split('#')[0] + '?' + urlencode({'notice_title':title,'notice_body':body,'notice_id':str(token)}) + '#notifications'
                send(title, body, token, notice_url)

    # One-time push test: Thursday, Nov 19, 2026 at 1:45 PM Houston time.
    # The 20-minute window accommodates GitHub Actions' ten-minute cron and minor delays.
    test_at = datetime(2026, 11, 19, 13, 45, tzinfo=ZoneInfo('America/Chicago'))
    if test_at <= now < test_at + timedelta(minutes=20):
        title = 'Test Reminder: 2:00 PM Zoom Prayer'
        body = "Today's Women's Zoom Prayer starts at 2:00 PM Houston time. This is a test of church app notifications."
        token = uuid.uuid5(uuid.NAMESPACE_URL, APP_ID + '/test/2026-11-19-1345-zoom-prayer')
        notice_url = BASE.split('#')[0] + '?' + urlencode({'notice_title': title, 'notice_body': body, 'notice_id': str(token)}) + '#notifications'
        send(title, body, token, notice_url)

    # Recurring meetings match the times shown on the church app homepage.
    weekly = [
        {'id':'womens-zoom-prayer','title':"Women's Zoom Prayer",'days':(0,1,2,3),'hour':14,'minute':0,'time':'2:00 PM','note':'Join the weekly Zoom prayer meeting.'},
        {'id':'friday-fasting-prayer','title':'Friday Fasting Prayer (Zoom)','days':(4,),'hour':10,'minute':0,'time':'10:00 AM','note':'Join the weekly fasting prayer on Zoom.'},
        {'id':'malayalam-sunday-school','title':'Malayalam Sunday School','days':(6,),'hour':9,'minute':15,'time':'9:15 AM','note':'Sunday School at church.'},
        {'id':'english-sunday-worship','title':'English Worship Service','days':(6,),'hour':10,'minute':0,'time':'10:00 AM','note':'Sunday worship at church.'},
        {'id':'english-sunday-school','title':'English Sunday School','days':(6,),'hour':11,'minute':0,'time':'11:00 AM','note':'Sunday School at church.'},
        {'id':'malayalam-sunday-worship','title':'Malayalam Worship Service','days':(6,),'hour':11,'minute':0,'time':'11:00 AM','note':'Sunday worship at church.'},
        {'id':'spanish-sunday-service','title':'Spanish Service','days':(6,),'hour':14,'minute':0,'time':'2:00 PM','note':'Sunday worship at church.'},
    ]
    for meeting in weekly:
        for minutes, label in [(1440, 'Tomorrow'), (60, 'Starting in 1 hour'), (30, 'Starting in 30 minutes')]:
            meeting_start = now.replace(hour=meeting['hour'], minute=meeting['minute'], second=0, microsecond=0)
            # 24-hour reminders happen on the preceding day.
            if minutes == 1440:
                meeting_start += timedelta(days=1)
            if meeting_start.weekday() not in meeting['days']:
                continue
            reminder_at = meeting_start - timedelta(minutes=minutes)
            if not (reminder_at <= now < reminder_at + timedelta(minutes=20)):
                continue
            title = label + ': ' + meeting['title']
            body = meeting['time'] + ' Houston time · ' + meeting['note']
            token = uuid.uuid3(uuid.NAMESPACE_URL, f'{APP_ID}/{meeting["id"]}/{meeting_start.date()}/{minutes}min')
            notice_url = BASE.split('#')[0] + '?' + urlencode({'notice_title':title,'notice_body':body,'notice_id':str(token)}) + '#notifications'
            send(title, body, token, notice_url)
    if history_changed:
        history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{today}: {count} reminder(s) {"previewed" if args.dry_run else "processed"}.')

if __name__ == '__main__':
    main()
