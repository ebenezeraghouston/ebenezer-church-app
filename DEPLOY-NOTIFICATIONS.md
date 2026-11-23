# Free GitHub Actions notification sender — setup

The app saves admin announcements to Firebase Firestore. The GitHub Actions workflow `.github/workflows/admin-push-notifications.yml` checks for pending messages approximately every 5 minutes and submits them to OneSignal. GitHub scheduled workflows can be delayed. The app status changes to **Accepted by OneSignal** when accepted; this does not guarantee device receipt.

## Step 1 — OneSignal REST API key
1. Sign in to OneSignal, open the existing Ebenezer AG app.
2. Find the app's REST API key in Settings → Keys & IDs (exact menu labels may differ).
3. In GitHub, open `ebenezeraghouston/ebenezer-church-app` → Settings → Secrets and variables → Actions → New repository secret.
4. Name: `ONESIGNAL_REST_API_KEY`. Paste the REST API key. Never paste it into a GitHub file or chat.

## Step 2 — Firebase service account
1. Firebase Console → project `ebenezer-ag-church-app` → Project settings → Service accounts.
2. Generate a **new private key** for a dedicated service account, or preferably create a dedicated service account in Google Cloud IAM with only **Cloud Datastore User** access to this Firestore database, then generate its JSON key. Treat the JSON as a highly sensitive credential.
3. In GitHub → Settings → Secrets and variables → Actions → New repository secret.
4. Name: `FIREBASE_SERVICE_ACCOUNT_JSON`. Paste the entire JSON key content.
5. Do not upload this key to the repository or share it publicly. Rotate/revoke it if exposed.

## Step 3 — Run the workflow
1. GitHub → Actions → **Church Admin Push Notifications (Free)**.
2. Select **Run workflow**. Check the logs. If there are queued announcements, this run may send them; verify that they were not already delivered by another system.
3. The workflow then checks automatically approximately every 5 minutes (subject to GitHub schedule delays).
4. Open the app → Admin Notifications → Recent Announcements. It refreshes approximately every 15 seconds while open.
5. Check OneSignal → Messages → Push to confirm the accepted push and test receipt on a subscribed phone.

## Notes
- Existing pending messages will be picked up when you first run the workflow. Review them before enabling the secrets if you do not want old notifications to go out.
- This only processes **adminAnnouncements**, not Devotions; devotion push alerts need separate work.
- **Queued** means Firestore accepted the request, not that OneSignal has received it.
- **Accepted by OneSignal** means the provider returned an ID, not that every phone received it.
- This design marks ambiguous errors as failed without automatically retrying, to reduce accidental duplicate pushes.
- GitHub Actions scheduled jobs can be delayed or disabled after repository inactivity; monitor the Actions page.
- Firestore usage and service-account credentials are subject to Firebase/Google Cloud terms and free-tier quotas. No Firebase Cloud Functions deployment is required.
