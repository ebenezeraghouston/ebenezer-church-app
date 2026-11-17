# Automatic Church Event Reminders — setup

This package contains the complete public church app and adds automatic OneSignal reminders **one day before** and **on the day of** each event, around **9:00 AM Houston time**. For multi-day events, both reminders refer to the first day only. Members must opt into push notifications. Delivery is not guaranteed on all devices.

## Upload
Upload **all files and folders**, including the hidden `.github/workflows` folder and `scripts` folder, into the **root** of your clean `ebenezer-church-app` repository. In GitHub's file uploader, check that `.github/workflows/church-event-reminders.yml` actually appears. Do not upload old repository files or `celebrations.json`.

## GitHub Actions configuration
Go to **Settings → Secrets and variables → Actions**:

1. Under **Repository secrets**, add `ONESIGNAL_REST_API_KEY` with your OneSignal app's REST API key. Never put this key in `index.html`, `events.json`, or other public files.
2. Under **Repository variables**, add `ONESIGNAL_APP_ID` with the OneSignal app ID. If you are using the original OneSignal app, it was `7aafcda2-45a3-4747-8527-e4f8a7b38692`; verify the app's origin and configuration in OneSignal before reusing it.
3. In **Settings → Actions → General**, allow workflow permissions **Read and write permissions**, so the reminder ledger can be committed. GitHub Actions may need to be enabled for the new repository.
4. In **Actions → Church Event Reminders (Day Before and Day Of) → Run workflow**, keep `dry_run` checked to test without sending. The log will print the current Houston date and any reminders due on that date. A test on a day without matching events will report no reminders due; this is normal.
5. To actually send reminders, leave the scheduled workflow enabled. It runs hourly but sends only when the Houston local hour is 9. GitHub scheduling can be delayed or skipped; delivery time is approximate.

## OneSignal and members
The website's OneSignal configuration must be tested for the **new** GitHub Pages site after the repository recreation. The public app uses the OneSignal SDK and `OneSignalSDKWorker.js`. Users must explicitly subscribe. On iPhone, web push generally requires the site added to Home Screen. A test push through the OneSignal dashboard is recommended before relying on event reminders.

## Edit reminders
Edit `events.json` to add or update events. Required fields: `id`, `date` (YYYY-MM-DD), `title`; optional `time`, `end`, `flyer`, `signup_url`. The workflow sends reminders at 9 AM Houston time on the previous calendar day and the event's start day. It stores only non-personal event reminder identifiers in `reminder-state.json` to prevent repeated sends. OneSignal's idempotency key also helps avoid duplicates. If you change an event date, update its `id` to match the new date.

## Privacy
No directory, birthdays, anniversaries, or personal household information is included. Never upload old `celebrations.json` or old repository history.
