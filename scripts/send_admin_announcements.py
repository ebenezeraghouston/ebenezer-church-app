"""Send administrator-approved announcement queue to subscribed church devices."""
import json, os, uuid
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import firebase_admin
from firebase_admin import credentials, firestore

APP_ID='85bfa892-43b6-40ec-8f07-255f95f6fd43'
APP_URL='https://ebenezeraghouston.github.io/ebenezer-church-app/'
def main():
    secret=os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')
    key=os.environ.get('ONESIGNAL_REST_API_KEY')
    if not secret or not key:
        raise SystemExit('Missing Firebase service account or OneSignal API key secrets')
    firebase_admin.initialize_app(credentials.Certificate(json.loads(secret)))
    db=firestore.client()
    now=datetime.now(timezone.utc)
    count=0
    for snap in db.collection('adminAnnouncements').where('status','==','pending').limit(20).stream():
        data=snap.to_dict()
        if not (3<=len(data.get('title',''))<=90 and 5<=len(data.get('message',''))<=500):
            snap.reference.update({'status':'error','error':'Invalid message length'})
            continue
        title=data['title'];body=data['message']
        token=str(uuid.uuid5(uuid.NAMESPACE_URL,'announcement/'+snap.id))
        url=APP_URL+'?'+urlencode({'notice_title':title,'notice_body':body,'notice_id':token})+'#notifications'
        payload={'app_id':APP_ID,'included_segments':['Total Subscriptions'],'target_channel':'push',
                 'headings':{'en':title},'contents':{'en':body},'url':url,'idempotency_key':token,'ttl':86400}
        req=Request('https://api.onesignal.com/notifications',data=json.dumps(payload).encode(),
                    headers={'Authorization':'Key '+key,'Content-Type':'application/json'},method='POST')
        try:
            with urlopen(req,timeout=30) as resp: result=json.load(resp)
            if not result.get('id'):
                print('OneSignal did not accept announcement',snap.id,result.get('errors'),flush=True)
                continue
            snap.reference.update({'status':'sent','sentAt':firestore.SERVER_TIMESTAMP,'pushId':result['id']})
            count+=1
            print('Sent announcement',snap.id,result['id'],flush=True)
        except Exception as e:
            print('Announcement send failed, will retry:',snap.id,str(e),flush=True)
    print('Announcements accepted:',count)
if __name__=='__main__': main()
