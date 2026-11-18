import {initializeApp} from 'https://www.gstatic.com/firebasejs/11.10.0/firebase-app.js';
import {getAuth,GoogleAuthProvider,signInWithPopup,signInWithRedirect,getRedirectResult,onAuthStateChanged,signOut} from 'https://www.gstatic.com/firebasejs/11.10.0/firebase-auth.js';
import {getFirestore,doc,getDoc,getDocs,collection,setDoc,addDoc,updateDoc,deleteDoc,serverTimestamp} from 'https://www.gstatic.com/firebasejs/11.10.0/firebase-firestore.js';
const config={apiKey:"AIzaSyDqRQoIYmEpEaK0-qFPuQeHU9YlPdREoF4",authDomain:"ebenezer-ag-church-app.firebaseapp.com",projectId:"ebenezer-ag-church-app",storageBucket:"ebenezer-ag-church-app.firebasestorage.app",messagingSenderId:"174964350833",appId:"1:174964350833:web:8a8b54d382410f49d560d0"};
const ADMIN_UID='xc2p3vvI9taVr4uPj1cW8n413oz1';
const $=id=>document.getElementById(id);
const status=$('directory-auth-status'),login=$('directory-sign-in'),logout=$('directory-sign-out'),account=$('directory-account'),request=$('directory-request'),members=$('directory-members'),adminPanel=$('directory-admin'),requests=$('directory-requests'),approvals=$('directory-approvals'),entries=$('directory-entries'),form=$('directory-form');
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\u0027':'&#39;'}[c]));
const message=(t)=>{status.textContent=t;};
let auth,db,user=null,isAdmin=false,isApproved=false;
const show=(el,yes)=>{el.hidden=!yes;};
function entryHTML(id,data,editable){
 const fields=[data.family,data.phone,data.email,data.notes].filter(Boolean).map(v=>'<p>'+esc(v)+'</p>').join('');
 return '<article class="panel" style="margin:12px 0"><strong>'+esc(data.name)+'</strong>'+fields+(editable?'<p><button class="btn" type="button" data-edit="'+esc(id)+'">Edit</button> <button class="btn" type="button" data-delete="'+esc(id)+'">Delete</button></p>':'')+'</article>';
}
async function refreshDirectory(){
 if(!user || !isApproved)return;
 entries.textContent='Loading directory…';
 try{
 const snap=await getDocs(collection(db,'directory'));
 const records=snap.docs.map(d=>({id:d.id,...d.data()})).sort((a,b)=>a.name.localeCompare(b.name));
 entries.innerHTML=records.length?records.map(r=>entryHTML(r.id,r,isAdmin)).join(''):'No directory entries have been added yet.';
 entries.querySelectorAll('[data-edit]').forEach(b=>b.addEventListener('click',()=>{
 const r=records.find(x=>x.id===b.dataset.edit);if(!r)return;
 $('directory-entry-id').value=r.id;
 for(const key of ['name','phone','email','family','notes'])$('directory-'+key).value=r[key]||'';
 $('directory-save').textContent='Save Changes';form.scrollIntoView({behavior:'smooth',block:'center'});
 }));
 entries.querySelectorAll('[data-delete]').forEach(b=>b.addEventListener('click',async()=>{
 if(!confirm('Delete this directory entry?'))return;
 try{await deleteDoc(doc(db,'directory',b.dataset.delete));await refreshDirectory();}catch(e){message('Could not delete entry: '+e.message);}
 }));
 }catch(e){entries.textContent='Directory could not be loaded: '+e.message;}
}
async function refreshAdmin(){
 if(!isAdmin)return;
 try{
 const [pending,approved]=await Promise.all([getDocs(collection(db,'accessRequests')),getDocs(collection(db,'approvedMembers'))]);
 const approvedIds=new Set(approved.docs.filter(d=>d.data().approved===true).map(d=>d.id));
 requests.innerHTML='';
 const waiting=pending.docs.filter(d=>!approvedIds.has(d.id));
 if(!waiting.length)requests.textContent='No pending access requests.';
 for(const d of waiting){
 const data=d.data(),line=document.createElement('div');line.className='panel';line.style.margin='10px 0';
 const title=document.createElement('p');title.textContent=(data.name||'Member')+' — '+(data.email||'');line.append(title);
 const btn=document.createElement('button');btn.className='btn';btn.textContent='Approve Member';line.append(btn);
 btn.addEventListener('click',async()=>{if(!confirm('Approve directory access for '+(data.email||d.id)+'?'))return;btn.disabled=true;try{await setDoc(doc(db,'approvedMembers',d.id),{approved:true,email:data.email||'',name:data.name||'',approvedAt:serverTimestamp()});await refreshAdmin();}catch(e){message('Approval failed: '+e.message);btn.disabled=false;}});
 requests.append(line);
 }
 approvals.innerHTML='';
 if(approved.empty)approvals.textContent='No approved members yet.';
 for(const d of approved.docs){
 const data=d.data(),line=document.createElement('div');line.className='panel';line.style.margin='10px 0';
 const title=document.createElement('p');title.textContent=(data.name||'Member')+' — '+(data.email||'')+' | '+(data.approved?'Approved':'Revoked');line.append(title);
 const btn=document.createElement('button');btn.className='btn';btn.textContent=data.approved?'Revoke Access':'Restore Access';line.append(btn);
 btn.addEventListener('click',async()=>{if(!confirm(btn.textContent+' for '+(data.email||d.id)+'?'))return;btn.disabled=true;try{await updateDoc(doc(db,'approvedMembers',d.id),{approved:!data.approved});await refreshAdmin();}catch(e){message('Update failed: '+e.message);btn.disabled=false;}});
 approvals.append(line);
 }
 }catch(e){requests.textContent='Could not load requests: '+e.message;}
}
async function updateUser(u){
 user=u;login.disabled=false;show(login,!u);show(logout,!!u);
 show(request,false);show(members,false);show(adminPanel,false);account.textContent='';
 if(!u){message('Sign in with Google to request access.');return;}
 account.textContent='Signed in: '+(u.email||'');
 isAdmin=u.uid===ADMIN_UID;isApproved=isAdmin;
 message('Checking private directory access…');
 try{
 if(!isAdmin){const approval=await getDoc(doc(db,'approvedMembers',u.uid));isApproved=approval.exists()&&approval.data().approved===true;}
 if(isApproved){message(isAdmin?'Administrator access enabled.':'Approved member access enabled.');show(members,true);show(adminPanel,isAdmin);await refreshDirectory();if(isAdmin)await refreshAdmin();}
 else{message('You are not an authorized user. Your Google account has not been approved to view the church directory. You may request access below.');show(request,true);const existing=await getDoc(doc(db,'accessRequests',u.uid));$('directory-request-button').disabled=existing.exists();$('directory-request-button').textContent=existing.exists()?'Request already submitted':'Request Directory Access';}
 }catch(e){message('Access check failed. Verify Firestore rules: '+e.message);}
}
try{
 auth=getAuth(initializeApp(config));db=getFirestore();const provider=new GoogleAuthProvider();
 onAuthStateChanged(auth,u=>updateUser(u).catch(e=>message('Sign-in error: '+e.message)));
 login.addEventListener('click',async()=>{login.disabled=true;message('Opening Google sign-in…');try{await signInWithPopup(auth,provider);}catch(e){if(e.code==='auth/popup-blocked'){await signInWithRedirect(auth,provider);}else{message('Sign-in failed: '+e.message);login.disabled=false;}}});
 logout.addEventListener('click',()=>signOut(auth).catch(e=>message('Sign-out failed: '+e.message)));
 getRedirectResult(auth).catch(e=>message('Google sign-in could not complete: '+e.message));
 $('directory-request-button').addEventListener('click',async()=>{if(!user)return;const b=$('directory-request-button');b.disabled=true;try{await setDoc(doc(db,'accessRequests',user.uid),{email:user.email||'',name:user.displayName||'',requestedAt:serverTimestamp()});b.textContent='Request submitted';message('You are not an authorized user yet. Your access request has been submitted and is awaiting church administrator approval.');}catch(e){message('Could not request access: '+e.message);b.disabled=false;}});
 form.addEventListener('submit',async e=>{e.preventDefault();if(!isAdmin)return;const id=$('directory-entry-id').value;const data={};for(const k of ['name','phone','email','family','notes'])data[k]=$('directory-'+k).value.trim();if(!data.name)return;
 const save=$('directory-save');save.disabled=true;
 try{if(id)await setDoc(doc(db,'directory',id),data);else await addDoc(collection(db,'directory'),data);form.reset();$('directory-entry-id').value='';save.textContent='Add Entry';message('Directory entry saved.');await refreshDirectory();}catch(err){message('Could not save: '+err.message);}finally{save.disabled=false;}
 });
 $('directory-cancel').addEventListener('click',()=>{form.reset();$('directory-entry-id').value='';$('directory-save').textContent='Add Entry';});
 $('directory-refresh').addEventListener('click',async()=>{if(user)await updateUser(user);});
}catch(e){message('Firebase setup error: '+e.message);}
