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
    parser.add_argument('--send-test', action='store_true', help='Send a one-time immediate test push, ignoring reminder schedule')
    parser.add_argument('--date', type=date.fromisoformat)
    parser.add_argument('--preview-time', help='Houston local HH:MM; dry run only')
    args = parser.parse_args()
    if (args.date or args.preview_time) and not args.dry_run:
        parser.error('--date and --preview-time require --dry-run')
    now = datetime.now(ZoneInfo('America/Chicago'))
    if args.preview_time or args.date:
        now = datetime.combine(args.date or now.date(), time.fromisoformat(args.preview_time) if args.preview_time else now.time(), ZoneInfo('America/Chicago'))
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
    def save_history():
        if not args.dry_run:
            temp = history_path.with_suffix('.tmp')
            temp.write_text(json.dumps(history, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            temp.replace(history_path)

    def send(title, body, token, url, expires_at=None, scheduled_at=None):
        nonlocal count, history_changed
        count += 1
        print(f'{title}: {body}', flush=True)
        if any(item.get('id') == str(token) and item.get('push_id') for item in history):
            print('OneSignal previously accepted; skipping duplicate:', token)
            return
        if args.dry_run:
            print('Preview delivery:', scheduled_at or now, flush=True)
            return
        payload = {'app_id': APP_ID, 'included_segments': ['Total Subscriptions'], 'target_channel': 'push', 'headings': {'en': title}, 'contents': {'en': body}, 'url': url, 'idempotency_key': str(token if token.version in (4, 5) else uuid.uuid5(uuid.NAMESPACE_URL, str(token))), 'ttl': 3600}
        if scheduled_at and scheduled_at > now:
            payload['send_after'] = scheduled_at.isoformat()
        req = Request('https://api.onesignal.com/notifications', data=json.dumps(payload).encode(), headers={'Authorization': 'Key ' + key, 'Content-Type': 'application/json'}, method='POST')
        with urlopen(req, timeout=30) as resp:
            result = json.load(resp)
        if not result.get('id'):
            errors = result.get('errors', 'unknown error')
            error_text = str(errors).lower()
            if 'all included players are not subscribed' in error_text or 'no subscribed' in error_text:
                print('WARNING: OneSignal has no eligible subscribed devices for this push. No notification was sent; leaving it unrecorded so a later run can retry.', flush=True)
                return False
            raise RuntimeError('OneSignal notification not accepted: ' + str(errors))
        print('OneSignal accepted notification:', result['id'])
        if not any(item.get('id') == str(token) and item.get('push_id') for item in history):
            history[:] = [item for item in history if item.get('id') != str(token)]
            history.insert(0, {'id':str(token), 'title':title, 'body':body, 'sent_at':now.isoformat(), 'push_id':result['id'], 'expires_at':expires_at, 'scheduled_for':scheduled_at.isoformat() if scheduled_at else None})
            history_changed = True
            save_history()
    # Cancel any previously queued individual Sunday service pushes, including
    # hourly alerts. The consolidated Sunday reminders replace them.
    sunday_titles = ('Malayalam Sunday School', 'English Worship Service', 'English Sunday School',
                     'Malayalam Worship Service', 'Spanish Service')
    if not args.dry_run:
        for item in list(history):
            if not any(name in item.get('title', '') for name in sunday_titles):
                continue
            scheduled = item.get('scheduled_for')
            if not scheduled or datetime.fromisoformat(scheduled) <= now:
                continue
            push_id = item.get('push_id')
            if not push_id:
                continue
            url = 'https://api.onesignal.com/notifications/' + push_id + '?' + urlencode({'app_id': APP_ID})
            try:
                with urlopen(Request(url, headers={'Authorization': 'Key ' + key}, method='DELETE'), timeout=30) as response:
                    print('Cancelled individual Sunday push:', push_id, response.status)
                history.remove(item)
                history_changed = True
            except Exception as error:
                print('WARNING: Unable to cancel individual Sunday push:', push_id, error, flush=True)

    # Remove previously scheduled hourly Women's Zoom Prayer notifications.
    # New reminders are limited to one push at 1:00 PM Houston time each meeting day.
    if not args.dry_run:
        for item in list(history):
            if "Women's Zoom Prayer" not in item.get('title', ''):
                continue
            # Preserve only the new once-daily 1 PM notification for its meeting date.
            # Older 'Today' notifications may also be queued hourly and must be cancelled.
            scheduled_date = None
            try:
                scheduled_date = datetime.fromisoformat(item.get('scheduled_for') or '').astimezone(ZoneInfo('America/Chicago')).date()
            except (ValueError, TypeError):
                pass
            expected_token = (str(uuid.uuid5(uuid.NAMESPACE_URL,
                f'{APP_ID}/womens-zoom-prayer/{scheduled_date}/1pm-only'))
                if scheduled_date else None)
            if item.get('id') == expected_token:
                continue
            scheduled = item.get('scheduled_for')
            if not scheduled or datetime.fromisoformat(scheduled) <= now:
                continue
            push_id = item.get('push_id')
            if not push_id:
                continue
            cancel_url = 'https://api.onesignal.com/notifications/' + push_id + '?' + urlencode({'app_id': APP_ID})
            try:
                with urlopen(Request(cancel_url, headers={'Authorization': 'Key ' + key}, method='DELETE'), timeout=30) as response:
                    print("Cancelled queued hourly Women's Zoom Prayer push:", push_id, response.status)
                history.remove(item)
                history_changed = True
            except Exception as error:
                print("WARNING: Unable to cancel queued Women's Zoom Prayer push:", push_id, error, flush=True)

    # Cancel obsolete queued fasting prayer reminders, retaining only 24h/1h alerts.
    if not args.dry_run:
        allowed = set()
        for event in events:
            if 'fasting prayer' not in event.get('title', '').lower():
                continue
            for start in event.get('start_times_local') or ([event['start_local']] if event.get('start_local') else []):
                dt = datetime.fromisoformat(start).replace(tzinfo=ZoneInfo('America/Chicago'))
                for minutes in (1440, 60):
                    allowed.add(str(uuid.uuid3(uuid.NAMESPACE_URL, f'{APP_ID}/{event["id"]}/{dt.isoformat()}/{minutes}min')))
        for offset in range(3):
            day = (now + timedelta(days=offset)).date()
            if day.weekday() == 4 and not any('fasting prayer' in e.get('title', '').lower() and any(datetime.fromisoformat(s).date() == day for s in e.get('start_times_local', [])) for e in events):
                for minutes in (1440, 60):
                    allowed.add(str(uuid.uuid3(uuid.NAMESPACE_URL, f'{APP_ID}/friday-fasting-prayer/{day}/{minutes}min')))
        for item in list(history):
            if 'fasting prayer' not in item.get('title', '').lower() or item.get('id') in allowed:
                continue
            scheduled = item.get('scheduled_for')
            if not scheduled or datetime.fromisoformat(scheduled) <= now or not item.get('push_id'):
                continue
            try:
                url = 'https://api.onesignal.com/notifications/' + item['push_id'] + '?' + urlencode({'app_id': APP_ID})
                with urlopen(Request(url, headers={'Authorization': 'Key ' + key}, method='DELETE'), timeout=30):
                    pass
                history.remove(item)
                history_changed = True
                save_history()
            except Exception as error:
                print('WARNING: Unable to cancel queued fasting prayer push:', error, flush=True)

    if args.send_test:
        if args.dry_run:
            parser.error('--send-test cannot be combined with --dry-run')
        title = 'Ebenezer AG — Push Notification Test'
        body = 'This is a test notification from the Ebenezer AG Church App. No action is needed.'
        token = uuid.uuid4()
        notice_url = BASE.split('#')[0] + '?' + urlencode({'notice_title': title, 'notice_body': body, 'notice_id': str(token)}) + '#notifications'
        send(title, body, token, notice_url)
        if history_changed:
            history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('Push test finished. Check the lines above for OneSignal acceptance or a no-subscribers warning.')
        return

    # Queue up to 36 hours ahead; allow a short late-start grace period.
    def reminder_eligible(reminder_at, event_start, minutes):
        grace = timedelta(minutes=120 if minutes == 1440 else 15)
        return reminder_at - timedelta(hours=36) <= now < reminder_at + grace

    # Exact-time events: previous day (24h) and at start.
    # No precise reminder is sent when the event has no confirmed start_local.
    for event in events:
        if event.get('reminders') is False:
            continue
        start_times = event.get('start_times_local') or ([event['start_local']] if event.get('start_local') else [])
        for start_text in start_times:
            event_start = datetime.fromisoformat(start_text).replace(tzinfo=ZoneInfo('America/Chicago'))
            for minutes in ((1440, 60) if 'fasting prayer' in event['title'].lower() else (1440, 0)):
                label = 'Tomorrow' if minutes == 1440 else ('In one hour' if minutes == 60 else 'Starting now')
                reminder_at = event_start - timedelta(minutes=minutes)
                if not reminder_eligible(reminder_at, event_start, minutes):
                    continue
                event_id = event.get('id') or (event['title'] + str(event.get('date', '')))
                token = uuid.uuid3(uuid.NAMESPACE_URL, f'{APP_ID}/{event_id}/{event_start.isoformat()}/{minutes}min')
                title = label + ': ' + event['title']
                body = (event_start.strftime('%a, %b %-d at %-I:%M %p') + ' Houston time · ' + ('FOOD SIGN-UP: Please sign up to bring a dish! GIFT EXCHANGE: Bring a gift ($25 maximum). Tap for the food sign-up link and details.' if event.get('id') == 'thanksgiving-2026-11-25' else event.get('note', 'See details in church app.')))
                notice_url = BASE.split('#')[0] + '?' + urlencode({'notice_title':title,'notice_body':body,'notice_id':str(token),'notice_expires':(event_start + timedelta(hours=1) if minutes == 0 else event_start).isoformat()}) + '#notifications'
                send(title, body, token, notice_url, (event_start + timedelta(hours=1) if minutes == 0 else event_start).isoformat(), reminder_at if reminder_at > now else None)

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
    # One consolidated Saturday evening notification and one Sunday morning notification.
    # All service times are Houston local time.
    for days_ahead in range(3):
        sunday = (now + timedelta(days=days_ahead)).date()
        if sunday.weekday() != 6:
            continue
        if sunday in (date(2027, 1, 3), date(2027, 1, 10)):
            continue
        sunday_start = datetime.combine(sunday, time(9, 15), ZoneInfo('America/Chicago'))
        expires_at = datetime.combine(sunday, time(14, 0), ZoneInfo('America/Chicago')).isoformat()
        body = ('Malayalam Sunday School 9:15 AM; English Worship 10:00 AM; '
                'English Sunday School 11:00 AM; Malayalam Worship 11:00 AM; '
                'Spanish Service 2:00 PM. All times Houston local.')
        for label, reminder_at in (
            ('Tomorrow', sunday_start - timedelta(days=1) + timedelta(hours=8, minutes=45)),
            ('Today', datetime.combine(sunday, time(8, 0), ZoneInfo('America/Chicago')))
        ):
            if not (reminder_at - timedelta(hours=36) <= now < sunday_start):
                continue
            if now > reminder_at + timedelta(minutes=30):
                continue
            title = label + ': Ebenezer AG Sunday Services'
            token = uuid.uuid5(uuid.NAMESPACE_URL, f'{APP_ID}/combined-sunday/{sunday}/{label}')
            notice_url = BASE.split('#')[0] + '?' + urlencode({'notice_title':title,'notice_body':body,'notice_id':str(token),'notice_expires':expires_at}) + '#notifications'
            send(title, body, token, notice_url, expires_at, reminder_at if reminder_at > now else None)

    for meeting in weekly:
        if meeting['days'] == (6,):
            continue  # Sunday services are covered by the combined reminders.
        for days_ahead in range(3):
            meeting_start = (now + timedelta(days=days_ahead)).replace(hour=meeting['hour'], minute=meeting['minute'], second=0, microsecond=0)
            if meeting_start.weekday() not in meeting['days']:
                continue
            # Fasting prayer replaces every regular gathering January 3–10, 2027.
            if date(2027, 1, 4) <= meeting_start.date() <= date(2027, 1, 9):
                continue
            # Women's Zoom Prayer: exactly one reminder per meeting day at 1 PM Houston time.
            if meeting['id'] == 'womens-zoom-prayer':
                reminder_at = meeting_start.replace(hour=13, minute=0)
                if reminder_at - timedelta(hours=36) <= now < meeting_start:
                    # Allow retry until the meeting starts if OneSignal has not accepted the push.
                    if now < meeting_start:
                        title = "Today: Women's Zoom Prayer at 2:00 PM"
                        body = 'Join the Zoom prayer meeting today at 2:00 PM Houston time.'
                        token = uuid.uuid5(uuid.NAMESPACE_URL, f'{APP_ID}/womens-zoom-prayer/{meeting_start.date()}/1pm-only')
                        notice_url = BASE.split('#')[0] + '?' + urlencode({'notice_title':title,'notice_body':body,'notice_id':str(token),'notice_expires':meeting_start.isoformat()}) + '#notifications'
                        send(title, body, token, notice_url, meeting_start.isoformat(), reminder_at if reminder_at > now else None)
                continue
            # Skip regular Friday prayer when a special fasting event covers it.
            if any('fasting prayer' in e.get('title', '').lower() and any(datetime.fromisoformat(s).date() == meeting_start.date() for s in e.get('start_times_local', [])) for e in events):
                continue
            for minutes in (1440, 60):
                label = 'Tomorrow' if minutes == 1440 else 'In one hour'
                reminder_at = meeting_start - timedelta(minutes=minutes)
                if not reminder_eligible(reminder_at, meeting_start, minutes):
                    continue
                title = label + ': ' + meeting['title']
                body = meeting['time'] + ' Houston time · ' + meeting['note']
                token = uuid.uuid3(uuid.NAMESPACE_URL, f'{APP_ID}/{meeting["id"]}/{meeting_start.date()}/{minutes}min')
                notice_url = BASE.split('#')[0] + '?' + urlencode({'notice_title':title,'notice_body':body,'notice_id':str(token),'notice_expires':(meeting_start + timedelta(hours=1) if minutes == 0 else meeting_start).isoformat()}) + '#notifications'
                send(title, body, token, notice_url, (meeting_start + timedelta(hours=1) if minutes == 0 else meeting_start).isoformat(), reminder_at if reminder_at > now else None)
    if history_changed:
        history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{today}: {count} reminder(s) {"previewed" if args.dry_run else "processed"}.')

if __name__ == '__main__':
    main()
