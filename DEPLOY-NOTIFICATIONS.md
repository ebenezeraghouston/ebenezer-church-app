# Deploy immediate admin push notifications

The GitHub Pages website cannot securely call OneSignal using its REST API key. The Firebase Cloud Function in `functions/index.js` sends each new `adminAnnouncements` document to OneSignal when created.

## Prerequisites
- Firebase project: `ebenezer-ag-church-app`
- Permission to deploy Cloud Functions, access Firestore, and manage secrets
- Firebase **Blaze (pay-as-you-go)** plan (Cloud Functions requires billing; usage charges may apply)
- OneSignal REST API key for the existing church app (never commit the key)

## Deploy from a computer
1. Install Node.js 22 and Firebase CLI: `npm install -g firebase-tools`.
2. Clone or download this GitHub repository, then open a terminal in its root.
3. Run `firebase login`.
4. Run `firebase use ebenezer-ag-church-app`.
5. Run `npm --prefix functions install`.
6. Run `firebase functions:secrets:set ONESIGNAL_REST_API_KEY` and paste your OneSignal **REST API key** when prompted.
7. Deploy the function: `firebase deploy --only functions:sendAdminAnnouncement`.
8. Publish the repaired Firestore security rules separately: `firebase deploy --only firestore:rules`. Review existing Firebase rules first if they have been edited outside GitHub.

## Verify
1. Open the church app as the existing admin and submit a **new** test announcement.
2. Recent Announcements will initially say "Queued for delivery", then "Sending to OneSignal…" and then "Accepted by OneSignal", or "Delivery failed". The history refreshes about every 15 seconds while the page is visible.
3. Check the OneSignal dashboard for the push and test receipt on a subscribed device. "Accepted by OneSignal" is **not** a guarantee that every device received it.
4. If needed, check Firebase Console → Functions → sendAdminAnnouncement → Logs.

**Important:** This function triggers on *newly created* announcements only. Old pending records will not be automatically sent. To avoid duplicates, verify their status in OneSignal before resending.

**Security:** Only the existing Firebase admin UID can create announcements under Firestore rules. The Cloud Function holds the OneSignal REST key in Firebase Secret Manager, not in the public website. Failed/ambiguous sends are not automatically retried because a network timeout after OneSignal accepts a request could otherwise cause duplicate notifications.

**Scope:** This function sends manually submitted Admin Notifications. Devotion publication notifications require a separate trigger and are not included in this deployment.
