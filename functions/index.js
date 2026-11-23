"use strict";
const { onDocumentCreated } = require("firebase-functions/v2/firestore");
const { defineSecret } = require("firebase-functions/params");
const { logger } = require("firebase-functions");
const { initializeApp } = require("firebase-admin/app");
const { getFirestore, FieldValue } = require("firebase-admin/firestore");

initializeApp();
const db = getFirestore();
const onesignalKey = defineSecret("ONESIGNAL_REST_API_KEY");
const APP_ID = "85bfa892-43b6-40ec-8f07-255f95f6fd43";
const APP_URL = "https://ebenezeraghouston.github.io/ebenezer-church-app/#notifications";

exports.sendAdminAnnouncement = onDocumentCreated({
  document: "adminAnnouncements/{announcementId}",
  region: "us-central1",
  secrets: [onesignalKey],
  retry: false,
  timeoutSeconds: 60,
}, async (event) => {
  const snapshot = event.data;
  if (!snapshot) return;
  const ref = snapshot.ref;
  const data = snapshot.data();
  if (data.status !== "pending") return;

  // Claim exactly once. Duplicate Firestore events must not send twice.
  const claimed = await db.runTransaction(async (tx) => {
    const current = await tx.get(ref);
    if (!current.exists || current.data().status !== "pending") return false;
    tx.update(ref, { status: "sending", processingAt: FieldValue.serverTimestamp() });
    return true;
  });
  if (!claimed) return;

  try {
    const response = await fetch("https://api.onesignal.com/notifications", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Key " + onesignalKey.value(),
      },
      body: JSON.stringify({
        app_id: APP_ID,
        target_channel: "push",
        included_segments: ["Subscribed Users"],
        headings: { en: data.title },
        contents: { en: data.message },
        url: APP_URL,
      }),
      signal: AbortSignal.timeout(20000),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || !payload.id) {
      throw new Error("OneSignal rejected request (HTTP " + response.status + "): " + JSON.stringify(payload).slice(0, 500));
    }
    await ref.update({
      status: "sent",
      sentAt: FieldValue.serverTimestamp(),
      onesignalId: payload.id,
      recipients: typeof payload.recipients === "number" ? payload.recipients : null,
    });
    logger.info("Announcement accepted by OneSignal", { id: event.params.announcementId, onesignalId: payload.id });
  } catch (error) {
    // No automatic retry: a timeout after OneSignal accepts could duplicate pushes.
    await ref.update({
      status: "failed",
      failedAt: FieldValue.serverTimestamp(),
      errorMessage: String(error.message || error).slice(0, 500),
    });
    logger.error("Announcement failed", { id: event.params.announcementId, error: String(error) });
  }
});
