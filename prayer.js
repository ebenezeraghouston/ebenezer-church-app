import {initializeApp,getApps,getApp} from 'https://www.gstatic.com/firebasejs/11.10.0/firebase-app.js';
import {getAuth,signInAnonymously,onAuthStateChanged} from 'https://www.gstatic.com/firebasejs/11.10.0/firebase-auth.js';
import {getFirestore,collection,addDoc,getDocs,query,where,doc,updateDoc,serverTimestamp,Timestamp} from 'https://www.gstatic.com/firebasejs/11.10.0/firebase-firestore.js';
const cfg={apiKey:"AIzaSyDqRQoIYmEpEaK0-qFPuQeHU9YlPdREoF4",authDomain:"ebenezer-ag-church-app.firebaseapp.com",projectId:"ebenezer-ag-church-app",appId:"1:174964350833:web:8a8b54d382410f49d560d0"};
const app=initializeApp(cfg,'prayer-public'),auth=getAuth(app),db=getFirestore(app);
const $=id=>document.getElementById(id),status=$('prayer-status'),list=$('prayer-list'),pending=$('prayer-pending'),adminPanel=$('prayer-admin');
let ready=false,admin=false;
const safe=t=>{const e=document.createElement('span');e.textContent=t;return e.innerHTML;};
function readIds(){try{return JSON.parse(localStorage.getItem('prayer-read')||'[]')}catch{return []}}
function markRead(id){try{localStorage.setItem('prayer-read',JSON.stringify([...new Set([...readIds(),id])].slice(-200)))}catch{}refresh();}
async function refresh(){
 try{
 const snap=await getDocs(query(collection(db,'prayerRequests'),where('status','==','approved')));
 const now=Date.now(),read=new Set(readIds());
 const items=snap.docs.filter(d=>d.data().expiresAt?.toMillis()>now&&!read.has(d.id)).sort((a,b)=>b.data().createdAt?.toMillis()-a.data().createdAt?.toMillis());
 list.innerHTML=items.length?'':'No unread prayer requests right now.';
 for(const d of items){const box=document.createElement('article');box.className='panel';box.style.margin='12px 0';const p=document.createElement('p');p.textContent=d.data().message;box.append(p);const b=document.createElement('button');b.className='btn';b.textContent='✓ Mark as Read';b.addEventListener('click',()=>markRead(d.id));box.append(b);list.append(box);}
 status.textContent='Approved prayer requests are available for up to 24 hours.';
 if(admin)await refreshPending();
 }catch(e){status.textContent='Unable to load prayer requests: '+e.message;}
}
async function refreshPending(){
 if(!admin)return;
 try{const snap=await getDocs(query(collection(db,'prayerRequests'),where('status','==','pending')));pending.innerHTML='';
 if(snap.empty)pending.textContent='No requests awaiting approval.';
 for(const d of snap.docs){const box=document.createElement('div');box.className='panel';const p=document.createElement('p');p.textContent=d.data().message;box.append(p);
 for(const [label,next] of [['Approve','approved'],['Reject','rejected']]){const b=document.createElement('button');b.className='btn';b.textContent=label;b.style.marginRight='8px';b.addEventListener('click',async()=>{b.disabled=true;try{await updateDoc(doc(db,'prayerRequests',d.id),{status:next,reviewedAt:serverTimestamp(),expiresAt:Timestamp.fromMillis(Date.now()+86400000)});await refresh();}catch(e){status.textContent='Could not update request: '+e.message;b.disabled=false;}});box.append(b);}
 pending.append(box);}
 }catch(e){pending.textContent='Could not load pending requests: '+e.message;}
}
window.addEventListener('ebenezer-auth-change',e=>{admin=!!e.detail.admin;adminPanel.hidden=!admin;if(admin)refreshPending();});
if(getApps().some(a=>a.name==='[DEFAULT]'))onAuthStateChanged(getAuth(getApp()),u=>{admin=u?.uid==='xc2p3vvI9taVr4uPj1cW8n413oz1';adminPanel.hidden=!admin;if(admin)refreshPending();});
onAuthStateChanged(auth,async u=>{if(!u){try{await signInAnonymously(auth)}catch(e){status.textContent='Prayer requests are unavailable until anonymous sign-in is enabled in Firebase: '+e.message;}return;}ready=true;refresh();});
$('prayer-form').addEventListener('submit',async e=>{e.preventDefault();if(!ready){status.textContent='Please wait for the connection.';return;}const input=$('prayer-message'),message=input.value.trim(),button=$('prayer-submit');if(message.length<10||message.length>500)return;button.disabled=true;
try{await addDoc(collection(db,'prayerRequests'),{message,status:'pending',createdAt:serverTimestamp(),expiresAt:Timestamp.fromMillis(Date.now()+86400000),submitterUid:auth.currentUser.uid});input.value='';status.textContent='Prayer request submitted for administrator approval. It will not be shared until approved.';}catch(err){status.textContent='Could not submit: '+err.message;}finally{button.disabled=false;}});
$('prayer-refresh').addEventListener('click',refresh);
