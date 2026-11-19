import {initializeApp,getApps} from 'https://www.gstatic.com/firebasejs/11.10.0/firebase-app.js';
import {getAuth,onAuthStateChanged} from 'https://www.gstatic.com/firebasejs/11.10.0/firebase-auth.js';
import {getFirestore,collection,doc,getDoc,getDocs,setDoc,serverTimestamp} from 'https://www.gstatic.com/firebasejs/11.10.0/firebase-firestore.js';
const cfg={apiKey:"AIzaSyDqRQoIYmEpEaK0-qFPuQeHU9YlPdREoF4",authDomain:"ebenezer-ag-church-app.firebaseapp.com",projectId:"ebenezer-ag-church-app",appId:"1:174964350833:web:8a8b54d382410f49d560d0"};
const app=getApps().find(a=>a.name==='[DEFAULT]')||initializeApp(cfg);
const auth=getAuth(app),db=getFirestore(app),ADMIN_UID='xc2p3vvI9taVr4uPj1cW8n413oz1';
const $=id=>document.getElementById(id),consent=$('receipt-consent'),status=$('receipt-auth-status'),panel=$('receipt-admin-panel'),results=$('receipt-admin-results'),adminStatus=$('receipt-admin-status');
let member=null,approved=false;
const consentKey='ebenezer-receipt-consent-v1';
function consentFor(uid){try{return JSON.parse(localStorage.getItem(consentKey)||'{}')[uid]===true}catch{return false}}
function setConsent(uid,value){try{const all=JSON.parse(localStorage.getItem(consentKey)||'{}');all[uid]=value;localStorage.setItem(consentKey,JSON.stringify(all))}catch{}}
onAuthStateChanged(auth,async u=>{
 member=null;approved=false;consent.disabled=true;consent.checked=false;panel.hidden=true;
 if(!u||!u.providerData.some(p=>p.providerId==='google.com')){status.textContent='Sign in with Google through the Church Directory to enable read receipts.';return}
 try{
  const admin=u.uid===ADMIN_UID;
  if(!admin){const d=await getDoc(doc(db,'approvedMembers',u.uid));if(!d.exists()||d.data().approved!==true){status.textContent='Read receipts are available to approved church members.';return}}
  if(auth.currentUser?.uid!==u.uid)return;
  member=u;approved=true;consent.disabled=false;consent.checked=consentFor(u.uid);
  status.textContent='Read receipts are optional and shared only with church administrators.';
  panel.hidden=!admin;if(admin)await refreshAdmin();
 }catch(e){status.textContent='Could not verify membership: '+e.message}
});
consent.addEventListener('change',()=>{if(member&&approved)setConsent(member.uid,consent.checked)});
window.addEventListener('ebenezer-notification-open',async e=>{
 if(!member||!approved||!consentFor(member.uid))return;
 const id=String(e.detail?.id||''),title=String(e.detail?.title||'Church Notification');
 if(!id||id.length>200)return;
 const u=member;
 // Deterministic receipt ID ensures one receipt per member per notification.
 const receiptId=encodeURIComponent(u.uid+'_'+id).replace(/%/g,'_').slice(0,800);
 try{await setDoc(doc(db,'notificationReceipts',receiptId),{notificationId:id,title:title.slice(0,200),memberUid:u.uid,memberName:(u.displayName||'Member').slice(0,120),memberEmail:u.email||'',openedAt:serverTimestamp()})}
 catch(err){console.warn('Notification read receipt could not be saved:',err.message)}
});
async function refreshAdmin(){
 if(auth.currentUser?.uid!==ADMIN_UID)return;
 adminStatus.textContent='Loading private tracking…';results.replaceChildren();
 try{
  const snap=await getDocs(collection(db,'notificationReceipts'));
  const grouped=new Map();
  for(const d of snap.docs){const x=d.data();if(!grouped.has(x.notificationId))grouped.set(x.notificationId,{title:x.title,readers:new Map()});
   const item=grouped.get(x.notificationId);if(!item.readers.has(x.memberUid))item.readers.set(x.memberUid,x);
  }
  adminStatus.textContent=grouped.size+' notification(s) with confirmed opens. Only opted-in members are counted.';
  for(const [id,entry] of grouped){
   const section=document.createElement('div');section.className='event';
   const heading=document.createElement('h3');heading.textContent=entry.title+' — '+entry.readers.size+' confirmed open(s)';section.append(heading);
   for(const x of entry.readers.values()){const p=document.createElement('p');const when=x.openedAt?.toDate?.();p.textContent=(x.memberName||'Member')+' ('+(x.memberEmail||'')+')'+(when?' · '+when.toLocaleString():'');section.append(p)}
   results.append(section);
  }
  if(!grouped.size)results.textContent='No members have opted in and opened a notification yet.';
 }catch(e){adminStatus.textContent='Tracking unavailable. Firestore rules must be published: '+e.message}
}
$('receipt-refresh').addEventListener('click',refreshAdmin);
