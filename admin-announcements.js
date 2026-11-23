import {initializeApp,getApps} from 'https://www.gstatic.com/firebasejs/11.10.0/firebase-app.js';
import {getAuth,onAuthStateChanged} from 'https://www.gstatic.com/firebasejs/11.10.0/firebase-auth.js';
import {getFirestore,collection,addDoc,getDocs,query,orderBy,limit,serverTimestamp} from 'https://www.gstatic.com/firebasejs/11.10.0/firebase-firestore.js';
const cfg={apiKey:"AIzaSyDqRQoIYmEpEaK0-qFPuQeHU9YlPdREoF4",authDomain:"ebenezer-ag-church-app.firebaseapp.com",projectId:"ebenezer-ag-church-app",appId:"1:174964350833:web:8a8b54d382410f49d560d0"};
const app=getApps().find(a=>a.name==='[DEFAULT]')||initializeApp(cfg);
const auth=getAuth(app),db=getFirestore(app);
const panel=document.getElementById('admin-announcement-panel'),form=document.getElementById('admin-announcement-form'),status=document.getElementById('announcement-feedback'),history=document.getElementById('announcement-history');
const title=document.getElementById('announcement-title'),message=document.getElementById('announcement-message'),send=document.getElementById('announcement-send');
const ADMIN_UID='xc2p3vvI9taVr4uPj1cW8n413oz1';
let isAdmin=false;
async function refresh(){
 if(!isAdmin)return;
 try{
  const snap=await getDocs(query(collection(db,'adminAnnouncements'),orderBy('createdAt','desc'),limit(15)));
  history.replaceChildren();
  const heading=document.createElement('h3');heading.textContent='Recent announcements';history.append(heading);
  if(snap.empty){const p=document.createElement('p');p.textContent='No announcements sent yet.';history.append(p);}
  for(const item of snap.docs){const d=item.data(),row=document.createElement('article');row.className='event';const name=document.createElement('strong');name.textContent=d.title;const p=document.createElement('p');p.textContent=d.message;const meta=document.createElement('small');meta.textContent='Status: '+(d.status==='sent'?'Accepted by OneSignal'+(typeof d.recipients==='number'?' ('+d.recipients+' targeted)':''):d.status==='sending'?'Sending to OneSignal…':d.status==='pending'?'Queued for delivery':d.status==='failed'?'Delivery failed — '+(d.errorMessage||'check function logs'):d.status||'Unknown');row.append(name,p,meta);history.append(row)}
 }catch(e){history.textContent='Unable to load announcement history: '+e.message}
}
onAuthStateChanged(auth,u=>{isAdmin=Boolean(u&&u.uid===ADMIN_UID&&!u.isAnonymous&&u.providerData.some(p=>p.providerId==='google.com'));panel.hidden=!isAdmin;if(isAdmin){refresh();setInterval(()=>{if(isAdmin&&!document.hidden)refresh()},15000)}});
document.getElementById('announcement-preview').addEventListener('click',()=>{status.textContent='Preview — '+(title.value.trim()||'(title)')+': '+(message.value.trim()||'(message)')});
form.addEventListener('submit',async e=>{
 e.preventDefault();
 if(!isAdmin){status.textContent='Administrator sign-in required.';return}
 const t=title.value.trim(),m=message.value.trim();
 if(t.length<3||t.length>90||m.length<5||m.length>500){status.textContent='Title must be 3–90 characters; message 5–500.';return}
 if(!confirm('Send this notification to ALL subscribed church devices?\n\n'+t+'\n'+m))return;
 send.disabled=true;status.textContent='Queuing notification securely…';
 try{await addDoc(collection(db,'adminAnnouncements'),{title:t,message:m,status:'pending',createdAt:serverTimestamp()});status.textContent='Notification queued for immediate processing. Check Recent Announcements for confirmation.';form.reset();await refresh()}
 catch(err){status.textContent='Could not queue notification: '+err.message+' Check that the updated Firestore security rules are published.'}
 finally{send.disabled=false}
});
