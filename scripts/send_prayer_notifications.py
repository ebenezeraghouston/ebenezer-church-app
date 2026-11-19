"""Moderated prayer notifications and expiration; requires Firebase service account secret."""
import json, os, uuid
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import firebase_admin
from firebase_admin import credentials, firestore

def main():
    secret=os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')
    key=os.environ.get('ONESIGNAL_REST_API_KEY')
    if not secret or not key:
        raise SystemExit('Configure FIREBASE_SERVICE_ACCOUNT_JSON and ONESIGNAL_REST_API_KEY GitHub Actions secrets.')
    firebase_admin.initialize_app(credentials.Certificate(json.loads(secret)))
    db=firestore.client()
    now=datetime.now(timezone.utc)
    requests=db.collection('prayerRequests')
    expired=0
    for snap in requests.where('expiresAt','<=',now).stream():
        snap.reference.delete()
        expired+=1
    sent=0
    for snap in requests.where('status','==','approved').stream():
        data=snap.to_dict()
        if data.get('notifiedAt') or data.get('expiresAt') is None or data['expiresAt']<=now:
            continue
        # Never send prayer text or personal details in lock-screen notifications.
        title='🙏 New Prayer Request'
        body='A prayer request has been approved. Open the church app to pray.'
        url='https://ebenezeraghouston.github.io/ebenezer-church-app/#prayer'
        payload={'app_id':'85bfa892-43b6-40ec-8f07-255f95f6fd43','included_segments':['Total Subscriptions'],'target_channel':'push','headings':{'en':title},'contents':{'en':body},'url':url,'idempotency_key':str(uuid.uuid5(uuid.NAMESPACE_URL,'prayer/'+snap.id)),'ttl':3600}
        req=Request('https://api.onesignal.com/notifications',data=json.dumps(payload).encode(),headers={'Authorization':'Key '+key,'Content-Type':'application/json'},method='POST')
        with urlopen(req,timeout=30) as response:
            result=json.load(response)
        if not result.get('id'):
            raise RuntimeError('OneSignal rejected prayer notification: '+str(result.get('errors')))
        snap.reference.update({'notifiedAt':firestore.SERVER_TIMESTAMP})
        sent+=1
    print(f'Prayer requests: {sent} notification(s), {expired} expired record(s) deleted.')

if __name__=='__main__':
    main()
