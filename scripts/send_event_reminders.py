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
            for minutes in (1440, 0):
                label = 'Tomorrow' if minutes == 1440 else 'Starting now'
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
            # Friday prayer: day before and at start only.
            for minutes in (1440, 0):
                label = 'Tomorrow' if minutes == 1440 else 'Starting now'
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
