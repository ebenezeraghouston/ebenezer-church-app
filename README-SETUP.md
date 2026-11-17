# Ebenezer AG — Fresh Public Church App

**Intended live URL:** https://ebenezeraghouston.github.io/ebenezer-church-app/

## Privacy
This is a fresh, standalone set of public-only files, not an export of the old repository. No celebrations.json, directory, member addresses, birthday or anniversary data, or old Git history are included. Public church leader names and the pastor family photo are included. Confirm permission to publish the photo and leaders' names.

## Publish without bringing old history back
1. KEEP the original `ebenezer-church-app` repository PRIVATE and GitHub Pages unpublished while preparing the new site.
2. Download a local backup if desired. The old backup contains sensitive member information; keep it offline and protected, and never upload it to the new public repository.
3. In the old repository Settings > General > Danger Zone, choose Delete this repository. **Only do this after confirming the backup and understanding this is irreversible.** Deletion removes the GitHub-hosted repo and its history but cannot recall forks, caches, clones or previous downloads. Do not simply make the old repository public.
4. Create a NEW, empty PUBLIC repository under `ebenezeraghouston` named EXACTLY `ebenezer-church-app`. Do NOT use GitHub Import, fork, template-from-old, clone/push the old history, or upload an old ZIP. Do not initialize with files from the old repository.
5. Upload only the CONTENTS of this ZIP to the root of the new repository, including the `assets` folder, `events.json`, `index.html`, `manifest.webmanifest`, `OneSignalSDKWorker.js`, `robots.txt`, `sitemap.xml`, and `.nojekyll`. Commit.
6. In Settings > Pages, deploy from branch `main`, folder `/ (root)`. Wait for deployment.
7. Open the app URL in a fresh/private browser session. Verify all six tabs and the absence of personal data. Confirm `.../celebrations.json` returns 404 (a site-wide 404 while unpublished is NOT enough).
8. Configure OneSignal for the same HTTPS site URL. The app uses existing OneSignal App ID, but permission and delivery are NOT verified. Test with a real device. Automated 24-hour/1-hour event reminders are NOT included; rebuild the reminder workflow using public `events.json` and GitHub Secrets if required. Do not assume reminders are active.
9. Google Analytics uses Measurement ID `G-NY7D4R99S1`. Check its Realtime report after publishing. Analytics cannot reliably count home-screen installations.
10. Update any QR codes or links only if your site URL changes (this package keeps the same URL).

## Notes
- `events.json` includes dates and details provided earlier; verify times and details before publication.
- `Giving` includes Zelle 417-274-1156 and Venmo @Ebenezer-AG from prior app context; independently confirm church account ownership before accepting donations.
- Google Search indexing can be requested after the new site is live.
- Deleting the original repo does not eliminate previously cached or copied personal data. If members' data was exposed, discuss appropriate notification and response steps with church leadership.
- This is a privacy-conscious rebuild, not a formal security audit.


## Modern home page / install instructions
The Home page now displays **Worship. Grow. Serve.** and a visible **Add to Home Screen** button. Android browsers supporting the PWA installation prompt can show an install dialog; iPhone Safari and browsers without that prompt receive manual instructions. The site must be deployed via HTTPS on GitHub Pages. Installing does not automatically grant notification permission.

This package contains no celebrations.json or private member directory. Do not import old repository history, backups, or personal files.


This update adds the user-provided sunset church photo, public event flyers, and food sign-up links. Upload all files including flyers/ and assets/. No member directory or celebrations.json is included.
