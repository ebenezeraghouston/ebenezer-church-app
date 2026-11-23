import {initializeApp,getApps} from 'https://www.gstatic.com/firebasejs/11.10.0/firebase-app.js';
import {getAuth,GoogleAuthProvider,signInWithPopup,onAuthStateChanged} from 'https://www.gstatic.com/firebasejs/11.10.0/firebase-auth.js';
import {getFirestore,collection,addDoc,getDocs,doc,updateDoc,query,where,serverTimestamp} from 'https://www.gstatic.com/firebasejs/11.10.0/firebase-firestore.js';
const cfg={apiKey:"AIzaSyDqRQoIYmEpEaK0-qFPuQeHU9YlPdREoF4",authDomain:"ebenezer-ag-church-app.firebaseapp.com",projectId:"ebenezer-ag-church-app",appId:"1:174964350833:web:8a8b54d382410f49d560d0"};
const app=getApps().find(a=>a.name==='[DEFAULT]')||initializeApp(cfg);
const auth=getAuth(app),db=getFirestore(app),$=id=>document.getElementById(id);
const EDITOR='gralex83@gmail.com',OWNER='xc2p3vvI9taVr4uPj1cW8n413oz1';
let editor=false,entries=[];
function permitted(u){return !!(u&&!u.isAnonymous&&u.providerData.some(p=>p.providerId==='google.com')&&(u.uid===OWNER||u.email?.toLowerCase()===EDITOR&&u.emailVerified));}
function dateLabel(t){return t?.toDate?.().toLocaleDateString('en-US',{year:'numeric',month:'long',day:'numeric'})||'Recently posted';}
function render(){
 const list=$('devotion-list');list.replaceChildren();
 const published=entries.filter(e=>e.status==='published');
 
 for(const e of published){
  const article=document.createElement('article');article.className='panel';
  const heading=document.createElement('h3');heading.textContent=e.title;
  const verse=document.createElement('p');verse.className='muted';verse.textContent=e.scripture;
  const message=document.createElement('p');message.style.whiteSpace='pre-wrap';message.textContent=e.body;
  const date=document.createElement('small');date.className='muted';date.textContent=e.devotionDate?new Date(e.devotionDate+'T12:00:00').toLocaleDateString('en-US',{year:'numeric',month:'long',day:'numeric'}):dateLabel(e.publishedAt);
  article.append(heading,verse,message,date);
  if(editor){const b=document.createElement('button');b.className='btn';b.textContent='Edit';b.style.marginLeft='12px';b.onclick=()=>{ $('devotion-id').value=e.id;$('devotion-title').value=e.title;$('devotion-scripture').value=e.scripture;$('devotion-body').value=e.body;$('devotion-date').value=e.devotionDate||new Date().toLocaleDateString('en-CA');$('devotion-editor').scrollIntoView({behavior:'smooth'});};article.append(b);}
  list.append(article);
 }
}
async function refresh(){
 try{const snap=await getDocs(query(collection(db,'devotions'),where('status','==','published')));entries=snap.docs.map(d=>({id:d.id,...d.data()})).sort((a,b)=>(b.publishedAt?.toMillis?.()||0)-(a.publishedAt?.toMillis?.()||0));$('devotion-status').textContent='';render();}
 catch(e){console.warn('Devotions could not load:',e);entries=[];render();$('devotion-status').textContent=e.code==='permission-denied'?'Devotions are temporarily unavailable. The church administrator needs to publish the updated Firebase security rules.':'Devotions are temporarily unavailable. Please try again later.';}
}
onAuthStateChanged(auth,u=>{
 editor=permitted(u);$('devotion-editor').hidden=!editor;$('devotion-login').hidden=editor;
 $('devotion-access').hidden=true;
});
$('devotion-login').onclick=async()=>{try{await signInWithPopup(auth,new GoogleAuthProvider());if(!permitted(auth.currentUser))$('devotion-status').textContent='This Google account does not have devotion publishing permission.';}catch(e){$('devotion-status').textContent='Sign-in failed: '+e.message;}};
$('devotion-form').onsubmit=async e=>{
 e.preventDefault();if(!permitted(auth.currentUser))return;
 const title=$('devotion-title').value.trim(),scripture=$('devotion-scripture').value.trim(),body=$('devotion-body').value.trim(),devotionDate=$('devotion-date').value,id=$('devotion-id').value;
 if(!/^\d{4}-\d{2}-\d{2}$/.test(devotionDate)||title.length<3||title.length>120||scripture.length<3||scripture.length>200||body.length<20||body.length>10000){$('devotion-status').textContent='Please check the title, Scripture and message lengths.';return;}
 if(!confirm('Publish this devotion for everyone to read?'))return;
 const btn=$('devotion-publish');btn.disabled=true;
 try{
  if(id){await updateDoc(doc(db,'devotions',id),{title,scripture,body,devotionDate,updatedAt:serverTimestamp()});}
  else{await addDoc(collection(db,'devotions'),{title,scripture,body,devotionDate,status:'published',authorEmail:auth.currentUser.email.toLowerCase(),publishedAt:serverTimestamp(),updatedAt:serverTimestamp()});}
  $('devotion-form').reset();$('devotion-id').value='';$('devotion-date').value=new Date().toLocaleDateString('en-CA');$('devotion-status').textContent='Devotion published. Notification delivery depends on the configured backend automation.';await refresh();
 }catch(err){$('devotion-status').textContent='Publish failed: '+err.message+' (Check deployed Firestore rules.)';}
 finally{btn.disabled=false;}
};
$('devotion-cancel').onclick=()=>{$('devotion-form').reset();$('devotion-id').value='';};
$('devotion-refresh').onclick=refresh;
$('devotion-date').value=new Date().toLocaleDateString('en-CA');
refresh();
