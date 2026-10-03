(()=>{
'use strict';
const C=window.APCS_WORKSPACE_CONFIG||{};
const DATA=window.APCS_WORKSPACE_DATA||[];
const $=q=>document.querySelector(q), $$=q=>[...document.querySelectorAll(q)];
const esc=x=>String(x??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const RESULTS=['未提交/未知','AC','WA','TLE','RE','CE'];
const ASSISTS=[['A0','完全獨立'],['A1','只有診斷'],['A2','概念提示'],['A3','方向提示'],['A4','骨架提示'],['A5','完整參考']];
const STAGES=['第一次接觸','理解觀念','獨立解題','限時實戰','複習驗證'];
const ERRORS=['讀題','演算法','資料結構','邊界條件','複雜度','實作Bug','語法'];
let cur=0,elapsed=0,running=false,tick=null,attemptStarted=false,attemptFinished=false;
let assist='',ind='',stage='',errors=[],scaffoldLevel=0,evidenceNotes={},audit=[],recordSaved=false;
const P=()=>DATA[cur];
const roleKey=p=>String(p.role||p.roleKey||'').toLowerCase();
const coreLike=p=>['core','transfer'].includes(roleKey(p));
const normText=s=>String(s??'').replace(/\s+/g,' ').trim();
function recordRoot(){return document.querySelector('#record')}
function exactText(root,text){
  const target=normText(text);
  return [...root.querySelectorAll('*')]
    .filter(e=>normText(e.textContent)===target)
    .sort((a,b)=>a.children.length-b.children.length||a.textContent.length-b.textContent.length)[0]||null;
}
function semanticBox(root,patterns){
  const ps=patterns.map(normText);
  const cand=[...root.querySelectorAll('.recordCard,.recordField,.fieldCard,label,div,section')]
    .filter(e=>{const t=normText(e.textContent);return t.length>0&&t.length<1400&&ps.some(p=>t.includes(p))})
    .sort((a,b)=>a.textContent.length-b.textContent.length);
  return cand[0]||root;
}
function commonParent(nodes,root){
  if(!nodes.length)return null;
  let p=nodes[0].parentElement;
  while(p&&p!==root){if(nodes.every(n=>p.contains(n)))return p;p=p.parentElement}
  return null;
}
function ensureHidden(root,id){
  let e=document.getElementById(id);
  if(!e){e=document.createElement('input');e.type='hidden';e.id=id;e.setAttribute('aria-hidden','true');root.appendChild(e)}
  return e;
}
function ensureContainer(root,id,tokens,labels,cls='choiceGrid'){
  let e=document.getElementById(id);if(e)return e;
  const btns=[...root.querySelectorAll('button,[role="button"]')].filter(b=>{
    const t=normText(b.textContent);
    return tokens.some(x=>t===x||t.startsWith(x+' ')||t.startsWith(x+'｜')||t.startsWith(x+'·'));
  });
  e=commonParent(btns,root);
  if(e&&e!==root){e.id=id;return e}
  const box=semanticBox(root,labels);
  e=document.createElement('div');e.id=id;e.className=cls;box.appendChild(e);return e;
}
function ensureControl(root,id,labels,selector,tag='input',attrs={}){
  let e=document.getElementById(id);if(e)return e;
  const box=semanticBox(root,labels);
  e=box.querySelector(selector);
  if(!e){
    e=document.createElement(tag);
    if(tag==='input')e.type=attrs.type||'text';
    if(tag==='textarea')e.rows=attrs.rows||3;
    e.className=attrs.className||'recordInput';
    box.appendChild(e);
  }
  e.id=id;return e;
}
function ensureButton(root,id,labels,buttonTexts){
  let e=document.getElementById(id);if(e)return e;
  const box=semanticBox(root,labels);
  e=[...box.querySelectorAll('button,[role="button"]')].find(b=>{
    const t=normText(b.textContent);return buttonTexts.some(x=>t.includes(x));
  });
  if(!e){e=document.createElement('button');e.type='button';e.className='btn secondary';e.textContent=buttonTexts[0];box.appendChild(e)}
  e.id=id;return e;
}
function bindIdentity(root,label,value){
  const lab=exactText(root,label);
  if(!lab)return false;
  let cell=lab.parentElement;
  for(let i=0;i<3&&cell&&cell!==root;i++){
    const values=[...cell.querySelectorAll('b,strong,.value,[data-value]')].filter(x=>x!==lab&&!x.contains(lab));
    if(values.length){
      lab.dataset.apcsIdentityLabel=label;
      cell.dataset.apcsIdentityCell=label;
      values[0].textContent=String(value??'—');
      values[0].dataset.apcsIdentityValue=label;
      return true;
    }
    cell=cell.parentElement;
  }
  const b=document.createElement('b');b.textContent=String(value??'—');lab.insertAdjacentElement('afterend',b);
  lab.dataset.apcsIdentityLabel=label;b.dataset.apcsIdentityValue=label;
  return true;
}
function ensureIdentityGrid(root){
  let grid=root.querySelector('#identityGrid,.identityGrid');
  if(!grid){
    grid=document.createElement('div');
    grid.id='identityGrid';
    grid.className='recordGrid identityGrid apcsIdentityRuntime';
  }else{
    if(!grid.id)grid.id='identityGrid';
    grid.classList.add('recordGrid','identityGrid','apcsIdentityRuntime');
  }
  const head=root.querySelector('.sectionHead');
  if(head){
    if(grid.previousElementSibling!==head)head.insertAdjacentElement('afterend',grid);
  }else if(grid.parentElement!==root||root.firstElementChild!==grid){
    root.insertAdjacentElement('afterbegin',grid);
  }
  grid.hidden=false;
  grid.removeAttribute('aria-hidden');
  grid.style.display='grid';
  grid.style.visibility='visible';
  grid.style.opacity='1';
  grid.dataset.apcsIdentityVisible='true';
  return grid;
}
function renderIdentityGrid(root,vals){
  root.querySelectorAll('[data-apcs-identity-label]').forEach(x=>x.removeAttribute('data-apcs-identity-label'));
  root.querySelectorAll('[data-apcs-identity-value]').forEach(x=>x.removeAttribute('data-apcs-identity-value'));
  root.querySelectorAll('[data-apcs-identity-cell]').forEach(x=>x.removeAttribute('data-apcs-identity-cell'));
  const grid=ensureIdentityGrid(root);
  grid.innerHTML=Object.entries(vals).map(([k,v])=>`<div class="identityCell" data-apcs-identity-cell="${esc(k)}"><span data-apcs-identity-label="${esc(k)}">${esc(k)}</span><b data-apcs-identity-value="${esc(k)}">${esc(v??'—')}</b></div>`).join('');
}
function setCanonicalIdentity(p){
  const root=recordRoot();if(!root)return;
  const vals={'PB UID':p.pb,'Problem ID':p.id||'—','Difficulty':p.d||'—','Role':p.roleLabel||p.role,'Source':p.source||p.judge||'Custom'};
  renderIdentityGrid(root,vals);
}
function ensureCanonicalRecordAdapter(){
  const root=recordRoot();if(!root)throw new Error('CANONICAL_RECORD_SECTION_MISSING');
  root.dataset.apcsRecordAdapter='semantic-v1';

  // State bridges are intentionally hidden; visible controls remain in canonical cards.
  for(const id of ['result','assist','ind','stage'])ensureHidden(root,id);

  ensureContainer(root,'resultChoices',RESULTS,['提交結果','Result'],'choiceGrid');
  ensureContainer(root,'assistChoices',ASSISTS.map(x=>x[0]),['Highest Assistance','Assistance'],'assistGrid');
  ensureContainer(root,'indChoices',['是','否'],['Independent','獨立'],'choiceGrid');
  ensureContainer(root,'stageChoices',STAGES,['Stage','作答階段'],'stageGrid');
  ensureContainer(root,'errs',ERRORS,['錯誤類型','Error'],'errGrid');

  const errBox=semanticBox(root,['錯誤類型','Error']);
  let ec=document.getElementById('errorCount');
  if(!ec){ec=[...errBox.querySelectorAll('span,small,div')].find(x=>/已選|selected/i.test(normText(x.textContent)));if(!ec){ec=document.createElement('span');errBox.appendChild(ec)}ec.id='errorCount'}
  ensureButton(root,'clearErrors',['錯誤類型','Error'],['清除','Clear']);

  const att=ensureControl(root,'att',['作答次數','Attempts'],'input[type="number"]','input',{type:'number'});
  att.min='1';att.step='1';
  const attBox=semanticBox(root,['作答次數','Attempts']);
  const attBtns=[...attBox.querySelectorAll('button')];
  let am=document.getElementById('attMinus')||attBtns.find(b=>/^[-−]$/.test(normText(b.textContent)));
  let ap=document.getElementById('attPlus')||attBtns.find(b=>/^\+$/.test(normText(b.textContent)));
  if(!am){am=document.createElement('button');am.type='button';am.textContent='−';attBox.appendChild(am)}am.id='attMinus';
  if(!ap){ap=document.createElement('button');ap.type='button';ap.textContent='+';attBox.appendChild(ap)}ap.id='attPlus';

  const mins=ensureControl(root,'mins',['本次分鐘','分鐘','Time'],'input[type="number"]','input',{type:'number'});
  mins.min='0';mins.step='0.5';
  const minBox=semanticBox(root,['本次分鐘','分鐘','Time']);
  const minBtns=[...minBox.querySelectorAll('button')];
  let mm=document.getElementById('minMinus')||minBtns.find(b=>/^[-−]$/.test(normText(b.textContent)));
  let mp=document.getElementById('minPlus')||minBtns.find(b=>/^\+$/.test(normText(b.textContent)));
  if(!mm){mm=document.createElement('button');mm.type='button';mm.textContent='−';minBox.appendChild(mm)}mm.id='minMinus';
  if(!mp){mp=document.createElement('button');mp.type='button';mp.textContent='+';minBox.appendChild(mp)}mp.id='minPlus';
  ensureButton(root,'syncTimer2',['本次分鐘','分鐘','Time'],['同步','計時']);

  const review=ensureControl(root,'review',['複習日期','Review'],'input[type="date"]','input',{type:'date'});review.type='date';
  ensureControl(root,'take',['核心收穫','Takeaway'],'textarea','textarea',{rows:3});

  const dw=semanticBox(root,['Direct Write','Write Key']);
  let wk=document.getElementById('writeKey')||dw.querySelector('input[type="password"],input[type="text"]');
  if(!wk){wk=document.createElement('input');wk.type='password';wk.placeholder='Write Key';dw.appendChild(wk)}wk.id='writeKey';
  ensureButton(root,'saveEndpoint',['Direct Write','Write Key'],['儲存','Save']);
  ensureButton(root,'clearEndpoint',['Direct Write','Write Key'],['清除','Clear']);

  let es=document.getElementById('endpointState');
  if(!es){es=document.createElement('div');es.className='helper';dw.appendChild(es);es.id='endpointState'}
  let gate=document.getElementById('gate');
  if(!gate){gate=document.createElement('div');gate.className='gate';dw.appendChild(gate);gate.id='gate'}
  ensureButton(root,'submitRec',['Direct Write','提交紀錄'],['提交紀錄','寫入','Submit']);
  let rs=document.getElementById('recSt');
  if(!rs){rs=document.createElement('div');rs.className='helper';dw.appendChild(rs);rs.id='recSt'}

  // Non-structural behavior helpers.
  const errs=document.getElementById('errs');
  if(errs&&!document.getElementById('errorSuggest')){const x=document.createElement('div');x.id='errorSuggest';x.className='behaviorFeedback';x.setAttribute('aria-live','polite');errs.insertAdjacentElement('afterend',x)}
  const take=document.getElementById('take');
  if(take&&!document.getElementById('takeQuality')){const x=document.createElement('div');x.id='takeQuality';x.className='behaviorFeedback';x.setAttribute('aria-live','polite');take.insertAdjacentElement('afterend',x)}
  if(gate&&!document.getElementById('recordInsight')){const x=document.createElement('div');x.id='recordInsight';x.className='behaviorFeedback recordInsight';x.setAttribute('aria-live','polite');gate.insertAdjacentElement('beforebegin',x)}

  // Optional existing canonical regions get IDs when identifiable.
  const preview=[...root.querySelectorAll('.recordPreview,.problemPreview,.recordTitle,strong,b')].find(x=>/PB-142|ZJ-a002/i.test(normText(x.textContent)));
  if(preview&&!document.getElementById('recordPreview'))preview.id='recordPreview';
  const evidence=semanticBox(root,['Evidence','證據']);
  if(evidence&&evidence!==root&&!document.getElementById('roleEvidence'))evidence.id='roleEvidence';
}
function ensureBehaviorHelpers(){ensureCanonicalRecordAdapter()}
const key=()=>`${C.ns||'apcs-v2-'}${P().pb}`;
function read(){try{return JSON.parse(localStorage.getItem(key())||'{}')}catch{return {}}}
function writeObj(o){localStorage.setItem(key(),JSON.stringify(o))}
function writebackId(){const o=read();if(o.writebackId)return o.writebackId;const id=`ui5133-${String(P().pb).toLowerCase()}-${crypto.randomUUID()}`;o.writebackId=id;writeObj(o);return id}
function state(){return {elapsed,attemptStarted,attemptFinished,assist,ind,stage,errors,scaffoldLevel,evidenceNotes,audit,recordSaved,plan:$('#planText').value,result:$('#result').value,att:$('#att').value,mins:$('#mins').value,review:$('#review').value,take:$('#take').value,writebackId:writebackId()}}
function save(){writeObj(state());$('#draftState').textContent='草稿已儲存';updateAllFeedback()}
function restore(){const o=read();elapsed=Number(o.elapsed)||0;attemptStarted=!!o.attemptStarted;attemptFinished=!!o.attemptFinished;assist=o.assist||'';ind=o.ind??'';stage=o.stage||'';errors=Array.isArray(o.errors)?o.errors:[];scaffoldLevel=Number(o.scaffoldLevel)||0;evidenceNotes=o.evidenceNotes||{};audit=Array.isArray(o.audit)?o.audit:[];recordSaved=!!o.recordSaved;$('#planText').value=o.plan||'';$('#result').value=o.result||'';$('#att').value=o.att||1;$('#mins').value=o.mins||0;$('#review').value=o.review||'';$('#take').value=o.take||'';clock();}
function roleRule(p){const r=roleKey(p);if(r==='worked')return '先預測，再查看逐步示範；看完後關閉參考內容，重新用自己的步驟完成一次。';if(r==='guided')return '先自己做第一版；卡住時再依序取得診斷、表示、規劃與實作提示，每次只開需要的一層。';if(r==='core')return '先保留完整獨立作答時間；需要提示時從最低層級開始，使用 A2 以上會記為非獨立完成。';if(r==='transfer')return '先從限制、資料關係與不變量自己辨認切入點；題前不直接揭露關鍵方法。';return '正式作答期間不開提示或解答；提交後再進入除錯與整理。'}
function startQuestion(p){return p.startQuestion||(()=>{const r=roleKey(p);if(r==='worked')return '先不要看示範：你會先追蹤哪個值、型別、index、state 或 candidate？';if(r==='guided')return '先寫下 representation / state / candidate，再決定第一個可驗證步驟。';if(r==='core')return '在不看提示下，你會如何建立 model、邊界測資與第一版解法？';if(r==='transfer')return '只看題目與限制，你認為真正需要保存或追蹤的是什麼？';return '先獨立完成正式 attempt。'})()}
function checks(p){if(Array.isArray(p.checks)&&p.checks.length)return p.checks;const arr=[{title:'Representation',body:'我能說清楚資料、candidate 或 state 各自代表什麼。'},{title:'Boundary',body:'我已檢查最小值、最後合法位置、重複與極端 case。'},{title:'Verification',body:'我有至少一個可手算的中間狀態或 targeted testcase。'},{title:'Assistance',body:'我知道本次最高使用到哪一層提示，稍後會如實記錄。'},{title:'Knowledge boundary',body:'我沒有把尚未學的技術當成題目前提。'}];if(coreLike(p))arr.push({title:'Independent semantics',body:'若使用 A2 以上提示，本次 Independent 必須記為否。'});return arr}
function doneItems(p){if(Array.isArray(p.done)&&p.done.length)return p.done;const x=[{title:'模型',body:p.debrief||p.summary||'能說清楚本題核心模型與 boundary。'},{title:roleKey(p)==='worked'?'重建':'作答證據',body:roleKey(p)==='worked'?'關掉 reference 後能重建 reasoning / implementation。':'留下可檢查的 attempt artifact，而不是只有 final answer。'},{title:'紀錄',body:'Result、Assistance、Independent 與 Stage 反映真實作答過程。'}];if(Array.isArray(p.s39Fields)&&p.s39Fields.length)x.push({title:'S39 artifacts',body:p.s39Fields.join(' · ')});if(p.optional)x.push({title:'Optional',body:'這題未完成不阻擋 Lesson / Unit completion。'});return x}
function flow(p){if(Array.isArray(p.planSteps)&&p.planSteps.length)return p.planSteps;const r=roleKey(p);if(r==='worked')return [{title:'Prediction',body:'先寫下預測與理由。'},{title:'Walkthrough',body:'對照示範中的每個 state change。'},{title:'Hide reference',body:'關閉示範，不靠短期記憶抄回。'},{title:'Reconstruction',body:'從空白重新完成。'},{title:'Debrief',body:'留下可遷移的規則。'}];if(r==='guided')return [{title:'Clean A0',body:'先自己做第一版。'},{title:'A1',body:'只診斷卡住的概念。'},{title:'A2',body:'需要時才看 representation。'},{title:'A3',body:'再整理解題 plan。'},{title:'A4',body:'最後才看 implementation skeleton。'}];if(r==='core')return [{title:'Clean A0',body:'完整獨立作答。'},{title:'Self-debug',body:'先用自己的測資定位問題。'},{title:'A1 if needed',body:'只在必要時取得有限診斷。'},{title:'Debrief',body:'完成後再看題後整理。'},{title:'Record',body:'保存真實 assistance 與結果。'}];if(r==='transfer')return [{title:'Constraints',body:'先讀限制。'},{title:'Representation',body:'自己選資料表示。'},{title:'Invariant',body:'找持續成立的關係。'},{title:'Implement',body:'完成與測試。'},{title:'Transfer',body:'整理換題後仍可用的規則。'}];return [{title:'Read',body:'讀題。'},{title:'Attempt',body:'正式作答。'},{title:'Submit',body:'提交。'},{title:'Debrief',body:'題後整理。'},{title:'Record',body:'完成紀錄。'}]}
function timerMilestones(p){const r=roleKey(p),a0=Math.max(1,Number(p.a0)||Math.min(8,Number(p.limit)||15)),lim=Math.max(a0,Number(p.limit)||15);if(r==='worked')return [{m:0,label:'預測',desc:'先留下自己的答案'},{m:Math.max(1,Math.round(lim*.3)),label:'逐步示範',desc:'Prediction 後才查看'},{m:Math.max(2,Math.round(lim*.55)),label:'關閉參考',desc:'把 reference 收起來'},{m:Math.max(3,Math.round(lim*.78)),label:'重建',desc:'從空白完成'},{m:lim,label:'整理',desc:'Debrief / record'}];if(r==='guided')return [{m:0,label:'Clean A0',desc:'先自己做'},{m:a0,label:'A1',desc:'可主動取得診斷'},{m:Math.min(lim,Math.max(a0+1,Math.round(lim*.6))),label:'A2/A3',desc:'需要時再開 representation / plan'},{m:Math.min(lim,Math.max(a0+2,Math.round(lim*.82))),label:'A4',desc:'最後才看 skeleton'},{m:lim,label:'首次上限',desc:'不 timeout'}];if(r==='core'||r==='transfer')return [{m:0,label:'Clean A0',desc:'保留獨立作答窗'},{m:a0,label:'A1 window',desc:'只提供有限診斷'},{m:lim,label:'首次上限',desc:'不自動 reveal、不 timeout'}];return [{m:0,label:'正式作答',desc:'提示鎖定'},{m:lim,label:'提交',desc:'提交後才 Debrief'}]}
function markAssist(a){const order=['A0','A1','A2','A3','A4','A5'];if(order.indexOf(a)>order.indexOf(assist))assist=a;if(coreLike(P())&&['A2','A3','A4','A5'].includes(assist))ind='false';save()}
function setSection(id){if(id==='deb'&&!attemptFinished&&roleKey(P())!=='worked'){toast('Debrief 尚未開放','先完成 attempt 與 self-audit。');return}$$('.sec').forEach(x=>x.classList.toggle('on',x.id===id));$$('.navBtn').forEach(x=>x.classList.toggle('on',x.dataset.s===id));if(id==='deb')renderDebrief();if(id==='record')renderRecord()}
function timerLimit(){return Math.max(1,Number(P().limit)||15)*60}
function a0Limit(){return Math.max(1,Number(P().a0)||Math.min(8,Number(P().limit)||15))*60}
function renderMilestones(){const p=P(),ms=timerMilestones(p),lim=Math.max(1,Number(p.limit)||15);$('#laneMarkers').innerHTML=ms.map(x=>`<span class="milestoneTick" style="left:${Math.min(100,Math.round(x.m/lim*100))}%" title="${esc(x.label)} · ${esc(x.desc)}"></span>`).join('');$('#timerMilestones').innerHTML=ms.map(x=>`<div class="milestoneItem ${elapsed>=x.m*60?'passed':''}"><b>${x.m}m · ${esc(x.label)}</b><span>${esc(x.desc)}</span></div>`).join('')}
function clock(){const lim=timerLimit(),a0=a0Limit(),pct=Math.min(100,Math.round(elapsed/lim*100));$('#clock').textContent=`${String(Math.floor(elapsed/60)).padStart(2,'0')}:${String(elapsed%60).padStart(2,'0')}`;$('#remaining').textContent=`剩餘 ${String(Math.max(0,Math.floor((lim-elapsed)/60))).padStart(2,'0')}:${String(Math.max(0,lim-elapsed)%60).padStart(2,'0')}`;$('#pct').textContent=pct+'%';$('#ring').style.background=`conic-gradient(var(--violet) ${pct}%,var(--panel4) ${pct}%)`;$('#laneFill').style.width=pct+'%';$('#phase').textContent=!attemptStarted?'按開始後進入本題計時。':elapsed<a0?'先完成自己的第一版；時間刻度只提醒目前階段，不會自動開提示。':elapsed<lim?'可視需要主動取得最低必要層級的協助；不會自動揭露。':'已超過首次上限；仍可繼續作答，不會 timeout。';$('#timerMeta').textContent=elapsed<a0?'獨立作答窗':'Assistance window';renderMilestones();if(document.activeElement!==$('#mins'))$('#mins').value=(elapsed/60).toFixed(1)}
function startTimer(){attemptStarted=true;if(!assist)assist='A0';if(running){clearInterval(tick);running=false;$('#start').textContent='繼續';save();return}running=true;$('#start').textContent='暫停';tick=setInterval(()=>{elapsed++;clock();if(elapsed%5===0)save()},1000);save()}
function resetTimer(){if(!confirm('重設本題 Timer 與 attempt 狀態？'))return;clearInterval(tick);running=false;elapsed=0;attemptStarted=false;attemptFinished=false;assist='';ind='';stage='';scaffoldLevel=0;audit=[];recordSaved=false;$('#start').textContent='開始';render();save()}
function renderFacts(){const p=P(),src=p.source||p.judge||'Custom';const rows=[['Difficulty',p.d||'—','fact-difficulty'],['Role',p.roleLabel||p.role,'fact-role'],['Skill',C.skill,'fact-skill'],['Time',`${p.a0||'—'}m A0 · ${p.limit||'—'}m upper`,'fact-time'],['OJ',src,'fact-oj']];$('#facts').innerHTML=rows.map(([a,b,cls])=>`<div class="factCard ${cls}"><span>${esc(a)}</span><b>${esc(b)}</b></div>`).join('');$('#judge').href=p.url||`${location.origin}/oj/problem/${encodeURIComponent(p.pb)}`;$('#judge').textContent=(p.judge==='Custom'||p.source==='Custom'||!p.url)?'在 APCS OJ 開啟題目 ↗':'開啟原題 ↗'}
function renderTask(){const p=P();$('#goal').textContent=p.goal||p.summary||'完成本題需要的 representation、reasoning 與 verification。';$('#startQ').textContent=startQuestion(p);$('#startAnswer').textContent=p.startAnswer||'先把你的第一個 model / state 寫下來，再依目前 Role 決定何時查看參考或取得協助。';$('#roleGuidance').innerHTML=`<b>${esc(p.roleLabel||p.role)}</b><p>${esc(p.roleGuide||roleRule(p))}</p>`;$('#known').innerHTML=(p.known||C.known||[]).map(x=>`<span class="tag boundaryKnown">${esc(x)}</span>`).join('');$('#blocked').innerHTML=(p.blocked||C.blocked||[]).map(x=>`<span class="tag boundaryBlocked">${esc(x)}</span>`).join('');$('#wins').innerHTML=doneItems(p).map((x,i)=>`<div class="doneItem"><span class="doneNo">${String(i+1).padStart(2,'0')}</span><span><b>${esc(x.title||'完成條件')}</b><small>${esc(x.body||x)}</small></span></div>`).join('');if(roleKey(p)==='worked'&&(p.walk||p.reference)){const ref=p.reference||p.walk;$('#workedWalkthrough').innerHTML=`<div class="card tone-cyan" style="margin-top:12px"><b>逐步示範</b><p class="small">先完成 Prediction，再展開；看完後請關閉並重新完成一次。</p><div id="workedRef" hidden>${esc(ref)}</div><button id="toggleRef" class="btn" type="button">顯示 / 隱藏示範</button></div>`;$('#toggleRef').onclick=()=>{attemptStarted=true;markAssist('A0');$('#workedRef').hidden=!$('#workedRef').hidden}}else $('#workedWalkthrough').innerHTML=''}
function renderPlan(){const p=P();$('#chevronFlow').innerHTML=flow(p).map((x,i)=>`<div class="chev"><b>0${i+1}</b><span><strong>${esc(x.title||x)}</strong><small>${esc(x.body||'')}</small></span></div>`).join('');const items=checks(p);$('#checkGrid').innerHTML=items.map((x,i)=>`<label class="checkTile" data-audit-card="${i}"><input type="checkbox" data-audit="${i}" ${audit.includes(i)?'checked':''}><span><b>${esc(x.title||'檢查')}</b><small>${esc(x.body||x)}</small></span></label>`).join('');$$('[data-audit]').forEach(x=>x.onchange=()=>{const i=Number(x.dataset.audit);audit=x.checked?[...new Set([...audit,i])]:audit.filter(v=>v!==i);renderAudit();save()});renderAudit()}
function renderAudit(){const total=$$('[data-audit]').length,done=$$('[data-audit]:checked').length;$$('[data-audit-card]').forEach(c=>{const i=Number(c.dataset.auditCard),on=audit.includes(i);c.style.borderColor=on?'var(--green)':'';c.style.background=on?'rgba(34,197,94,.08)':''});$('#auditProgress').innerHTML=`<b>Self-audit ${done}/${total}</b><span>${done===total&&total?'已完成，可結束 attempt。':'勾選不是裝飾；完成狀態會保存並控制 Debrief gate。'}</span>`;$('#finishAttempt').disabled=!(attemptStarted&&total>0&&done===total&&$('#planText').value.trim().length>=8)}
function nextScaffold(){const p=P();if(!attemptStarted)return {ok:false,msg:'先開始 attempt，保留 clean A0。'};const arr=Array.isArray(p.scaffolds)&&p.scaffolds.length?p.scaffolds:['先說明 representation / state 的語意。','畫出最小 trace / mapping。','寫出 plan / invariant。','整理 implementation skeleton。'];if(coreLike(p)){if(scaffoldLevel===0){scaffoldLevel=1;markAssist('A1');return {ok:true,level:'A1',text:arr[0]}}scaffoldLevel=Math.min(4,scaffoldLevel+1);const a='A'+scaffoldLevel;markAssist(a);ind='false';save();return {ok:true,level:a,text:arr[scaffoldLevel-1]}}scaffoldLevel=Math.min(4,scaffoldLevel+1);const a='A'+scaffoldLevel;markAssist(a);return {ok:true,level:a,text:arr[scaffoldLevel-1]}}
function coachAllowed(mode){const p=P();if(mode==='problem')return {ok:true};if(roleKey(p)==='mock'&&!attemptFinished)return {ok:false,msg:'Mock attempt 尚未完成。'};if(coreLike(p)&&!attemptStarted&&['hint','debug','solution'].includes(mode))return {ok:false,msg:'先開始 clean A0 attempt。'};return {ok:true}}
function coachPrompt(mode){const p=P(),level=assist||'A0';return `/${mode}\n\n[CONTEXT]\nunit: ${C.unit}\nlesson: ${C.lesson}\ntarget_skill: ${C.skill}\nknown: ${(C.known||[]).join('; ')}\nnot_yet_learned: ${(C.blocked||[]).join('; ')}\nrole: ${p.roleLabel||p.role}\nassistance_so_far: ${level}\n[/CONTEXT]\n\n[PROBLEM]\npb_uid: ${p.pb}\nproblem_id: ${p.id||''}\ntitle: ${p.title}\njudge: ${p.judge||'Custom'}\n[/PROBLEM]\n\n[ROLE_CONTRACT]\n${roleRule(p)}\n[/ROLE_CONTRACT]`}
async function coach(mode){const allow=coachAllowed(mode);if(!allow.ok){$('#copySt').textContent=allow.msg;return}if(mode==='hint'){const h=nextScaffold();if(!h.ok){$('#copySt').textContent=h.msg;return}$('#scaffoldBox').style.display='block';$('#scaffoldBox').innerHTML=`<b>${h.level}</b><p>${esc(h.text)}</p>`}if(mode==='solution')markAssist('A5');if(mode==='debug'&&attemptStarted)markAssist('A1');const text=coachPrompt(mode);$('#promptPreview').textContent=text;try{await navigator.clipboard.writeText(text);$('#copySt').textContent=`已複製 /${mode} canonical context。`}catch{$('#copySt').textContent='已產生 context；瀏覽器未允許自動複製。'}renderControls();save()}
function renderCoach(){const p=P();$('#coachUse').textContent=p.coachUse||'先自己完成目前能做的部分。需要協助時只取最低必要層級；若是 Core / Transfer，A2 以上會自動記為非獨立。';$$('.modeCard').forEach(b=>{const a=coachAllowed(b.dataset.m);b.classList.toggle('locked',!a.ok);b.querySelector('.lockMsg').textContent=a.ok?'':a.msg})}
function renderDebrief(tab='trigger'){const p=P();if(!attemptFinished&&roleKey(p)!=='worked'){ $('#debody').innerHTML='<div class="protectedMsg">先完成 attempt + self-audit，才開放題後整理。</div>';return}const d=p.debrief6||{};const map={trigger:d.trigger||'回想你最初看到什麼訊號，才決定這樣表示或枚舉。',baseline:d.baseline||p.debrief||p.summary||'把第一版方法與後來的修正分開整理。',correctness:d.correctness||'說明為什麼不漏、不重複，以及哪個 invariant / boundary 保證正確。',cpp:d.cpp||'保留一個真正影響實作的 C++ 細節，例如型別、index、容器或 update order。',pitfalls:d.pitfalls||'記下第一個 root cause、最小反例，以及下一次可更早發現它的方法。',transfer:d.transfer||(p.optional?'這是 Optional Transfer；整理能帶到陌生題的規則即可。':'寫下一個換題目表面後仍可沿用的 representation / invariant / testing rule。')};$('#debody').innerHTML=`<div class="debriefProduct"><h3>${esc(({trigger:'觸發訊號',baseline:'基準 → 推導',correctness:'正確性',cpp:'C++ 實作',pitfalls:'風險 / 反例',transfer:'測資與遷移'})[tab]||'題後整理')}</h3><p>${esc(map[tab]||map.trigger)}</p></div>`;if(Array.isArray(p.s39Fields)&&p.s39Fields.length){$('#s39Evidence').innerHTML='<div class="eyebrow">S39 作答產物</div>'+p.s39Fields.map((x,i)=>`<label class="recordCard full"><span class="label">${esc(x)}</span><textarea data-ev="${i}" rows="2">${esc(evidenceNotes[i]||'')}</textarea></label>`).join('');$$('[data-ev]').forEach(x=>x.oninput=()=>{evidenceNotes[x.dataset.ev]=x.value;save()})}else $('#s39Evidence').innerHTML=''}
function setResult(v){$('#result').value=v;renderControls();save()}
function renderControls(){const p=P();$('#resultChoices').innerHTML=RESULTS.map(x=>`<button type="button" class="choice ${$('#result').value===x?'on':''}" data-result="${esc(x)}"><span class="choiceName">${esc(x)}</span></button>`).join('');$$('[data-result]').forEach(b=>b.onclick=()=>setResult(b.dataset.result));$('#assistChoices').innerHTML=ASSISTS.map(([a,t])=>`<button type="button" class="assistChoice ${assist===a?'on':''}" data-a="${a}"><span class="choiceCode">${a}</span><span class="choiceName">${t}</span></button>`).join('');$$('[data-a]').forEach(b=>b.onclick=()=>{assist=b.dataset.a;if(coreLike(p)&&['A2','A3','A4','A5'].includes(assist))ind='false';renderControls();save()});$('#assist').value=assist;$('#indChoices').innerHTML=[['true','是'],['false','否']].map(([v,t])=>`<button type="button" class="choice ${ind===v?'on':''}" data-ind="${v}"><span class="choiceName">${t}</span></button>`).join('');$$('[data-ind]').forEach(b=>b.onclick=()=>{ind=b.dataset.ind;renderControls();save()});$('#ind').value=ind;$('#stageChoices').innerHTML=STAGES.map(x=>`<button type="button" class="stageChoice ${stage===x?'on':''}" data-stage="${esc(x)}">${esc(x)}</button>`).join('');$$('[data-stage]').forEach(b=>b.onclick=()=>{stage=b.dataset.stage;renderControls();save()});$('#stage').value=stage;$('#errs').innerHTML=ERRORS.map(x=>`<button type="button" class="errChip ${errors.includes(x)?'on':''}" data-err="${esc(x)}">${esc(x)}</button>`).join('');$$('[data-err]').forEach(b=>b.onclick=()=>{const x=b.dataset.err;errors=errors.includes(x)?errors.filter(y=>y!==x):[...errors,x];renderControls();save()});$('#errorCount').textContent=`${errors.length} 已選`;updateAllFeedback();renderGate()}
function recommendation(){const s={result:$('#result').value,assist,ind,stage};let days=3,reason='';if(s.result==='AC'){if(s.assist==='A0'&&s.ind==='true'){days=s.stage==='複習驗證'?14:7;reason='低 Assistance 且獨立完成：拉開間隔做 delayed verification。'}else if(['A1','A2'].includes(s.assist)){days=3;reason='已完成但仍有低階提示：縮短間隔確認支架能否撤掉。'}else{days=1;reason='Assistance 偏高：隔天重做，避免只記住剛看過的解法。'}}else if(s.result==='未提交/未知'||!s.result){days=1;reason='尚未有穩定提交結果：24 小時內回來完成。'}else{days=1;reason='本次未通過：隔天優先修正第一個 root cause。'}if(roleKey(P())==='worked'&&s.result==='AC')reason='Worked Example：複習重點是關掉 reference 後重建。';if(roleKey(P())==='transfer'&&s.result==='AC'&&s.assist==='A0'&&s.ind==='true'){days=10;reason='Transfer 在 A0 獨立完成：隔更久並換外觀題驗證遷移。'}return {days,reason}}
function updateAllFeedback(){ensureBehaviorHelpers();const r=$('#result').value;let tip='先選提交結果，系統才會提供錯誤診斷與複習建議。';if(r==='WA')tip='WA：先分辨讀題 / 演算法 / 邊界條件 / 實作Bug 哪一層最早出錯。';if(r==='TLE')tip='TLE：回到 operation count 與 constraints，避免只做微小常數優化。';if(r==='RE')tip='RE：先檢查邊界條件、非法索引與狀態第一次失效的位置。';if(r==='CE')tip='CE：修語法後仍要回到原本 reasoning，不把編譯成功當成解題完成。';if(r==='AC'&&errors.length)tip='已 AC 仍可保留真正 root cause，供 delayed review 使用。';if($('#errorSuggest'))$('#errorSuggest').textContent=tip;const rec=recommendation();if($('#recordInsight'))$('#recordInsight').innerHTML=`<b>建議 ${rec.days} 天後複習</b><span>${esc(rec.reason)}</span>`;const t=$('#take').value.trim();let q='尚未填寫';if(t.length>=20&&/(因為|所以|邊界|狀態|複雜度|invariant|index|trace|反例|測資)/i.test(t))q='具體，可作 delayed review 提示';else if(t.length>=10)q='已有內容；再補一個可檢查的原因 / boundary';if($('#takeQuality'))$('#takeQuality').textContent=`收穫品質：${q}`;renderAudit();renderGate()}
function renderGate(){const miss=[];if(!attemptFinished&&roleKey(P())!=='worked')miss.push('Attempt 尚未完成');if(!$('#result').value)miss.push('Result');if(!assist)miss.push('Highest Assistance');if(!ind)miss.push('Independent?');if(!stage)miss.push('Stage');if(coreLike(P())&&['A2','A3','A4','A5'].includes(assist)&&ind!=='false')miss.push('A2+ requires independent=false');if($('#take').value.trim().length<8)miss.push('核心收穫至少 8 字');$('#gate').innerHTML=miss.length?`<div class="gateRow bad"><span class="gateDot"></span><b>尚未可提交：</b> ${esc(miss.join(' · '))}</div>`:'<div class="gateRow good"><span class="gateDot"></span><b>Record facts 已明確確認。</b></div>';$('#submitRec').disabled=miss.length>0}
function renderRecord(){const p=P();ensureCanonicalRecordAdapter();setCanonicalIdentity(p);if($('#recordPreview'))$('#recordPreview').textContent=`${p.id||p.pb}｜${p.title}`;if($('#roleEvidence'))$('#roleEvidence').innerHTML=`<b>${esc(p.evidence||'Learning-only')}</b><span>${esc(p.recordNote||'完成紀錄只保存本次作答 facts；Problem metadata 仍以 Problem Bank 為準。')}</span>`;renderControls()}
async function submitRecord(){renderGate();if($('#submitRec').disabled)return;const keyv=(localStorage.getItem('apcs-rec-write-key')||'').trim();if(!keyv){$('#recSt').textContent='請先在 Direct Write 設定儲存 Write Key。';return}const body={pb_uid:P().pb,writeback_id:writebackId(),latest_result:$('#result').value,assistance:assist,independent:ind==='true',attempts:Math.max(1,Number($('#att').value)||1),time_min:Math.max(0,Number($('#mins').value)||0),stage,error_types:errors,review_date:$('#review').value||'',core_takeaway:$('#take').value.trim()};$('#recSt').textContent='寫入中…';try{const r=await fetch('/api/record',{method:'POST',headers:{'Content-Type':'application/json','X-APCS-Write-Key':keyv},body:JSON.stringify(body)});const j=await r.json().catch(()=>({}));if(!r.ok||!j.ok)throw new Error(j.error||`HTTP ${r.status}`);recordSaved=true;save();$('#recSt').textContent=j.duplicate?'已存在相同 Writeback ID；未建立重複紀錄。':`REC-v3.1 寫入成功${j.rec_uid?' · '+j.rec_uid:''}`}catch(e){$('#recSt').textContent=`寫入失敗：${e.message}`}}
function toast(title,body){$('#toastTitle').textContent=title;$('#toastBody').textContent=body;$('#toast').classList.add('show');setTimeout(()=>$('#toast').classList.remove('show'),2200)}
function render(){const p=P();$$('.problemBtn').forEach((b,i)=>b.classList.toggle('on',i===cur));renderFacts();renderTask();renderPlan();renderCoach();renderDebrief();renderRecord();clock();$('#systemState').textContent=`${C.lesson} · 草稿保存在本機 · 完成後可寫入 REC-v3.1`;}
function selectProblem(i){save();cur=i;clearInterval(tick);running=false;$('#start').textContent='開始';restore();render();const u=new URL(location.href);u.searchParams.set('pb',P().pb);history.replaceState(null,'',u)}
function bind(){
  $$('.problemBtn').forEach((b,i)=>b.onclick=()=>selectProblem(i));$$('.navBtn').forEach(b=>b.onclick=()=>setSection(b.dataset.s));$$('.modeCard').forEach(b=>b.onclick=()=>coach(b.dataset.m));$$('.tabBtn').forEach(b=>b.onclick=()=>{$$('.tabBtn').forEach(x=>x.classList.toggle('on',x===b));renderDebrief(b.dataset.t)});
  $('#start').onclick=startTimer;$('#reset').onclick=resetTimer;$('#syncTimer').onclick=()=>{$('#mins').value=(elapsed/60).toFixed(1);save()};$('#syncTimer2').onclick=$('#syncTimer').onclick;
  $('#finishAttempt').onclick=()=>{renderAudit();if($('#finishAttempt').disabled){toast('還不能完成','先完成 plan + 全部 self-audit。');return}attemptStarted=true;attemptFinished=true;if(!assist)assist='A0';save();setSection('deb')};
  $('#attMinus').onclick=()=>{$('#att').value=Math.max(1,Number($('#att').value)-1);save()};$('#attPlus').onclick=()=>{$('#att').value=Number($('#att').value)+1;save()};$('#minMinus').onclick=()=>{$('#mins').value=Math.max(0,Number($('#mins').value)-1).toFixed(1);save()};$('#minPlus').onclick=()=>{$('#mins').value=(Number($('#mins').value)+1).toFixed(1);save()};$('#clearErrors').onclick=()=>{errors=[];renderControls();save()};
  $('#saveEndpoint').onclick=()=>{const k=$('#writeKey').value.trim();if(k.length<24){toast('Write Key 無效','請使用原本產生的長隨機值。');return}localStorage.setItem('apcs-rec-write-key',k);$('#endpointState').textContent='Write Key 已存於本機'};$('#clearEndpoint').onclick=()=>{localStorage.removeItem('apcs-rec-write-key');$('#writeKey').value='';$('#endpointState').textContent='Write Key 已清除'};$('#submitRec').onclick=submitRecord;
  ['planText','att','mins','review','take'].forEach(id=>$('#'+id).addEventListener('input',()=>{if(id==='planText')attemptStarted=true;save()}));window.addEventListener('keydown',e=>{if(e.altKey&&/^[1-5]$/.test(e.key)){e.preventDefault();setSection(['task','plan','coach','deb','record'][Number(e.key)-1])}})
}
const requested=new URL(location.href).searchParams.get('pb');const idx=DATA.findIndex(x=>x.pb===requested);if(requested&&idx<0){$('#routeDiagnostic').style.display='block';$('#routeDiagnostic').textContent=`路徑診斷：${requested} 不屬於 ${C.lesson}；已 fail-closed 到 ${C.def}`};cur=idx>=0?idx:Math.max(0,DATA.findIndex(x=>x.pb===C.def));ensureCanonicalRecordAdapter();$('#writeKey').value=localStorage.getItem('apcs-rec-write-key')||'';restore();bind();render();
window.__APCS_WORKSPACE_V3__={state:()=>state(),selectProblem,renderGate,renderAudit,recordReady:()=>!$('#submitRec').disabled,timerMilestones:()=>timerMilestones(P()),recordAdapter:()=>recordRoot()?.dataset.apcsRecordAdapter||'',identityLabels:()=>['PB UID','Problem ID','Difficulty','Role','Source'].filter(k=>recordRoot()?.querySelector(`[data-apcs-identity-label="${k}"]`)),identityVisible:()=>['PB UID','Problem ID','Difficulty','Role','Source'].map(k=>{const l=recordRoot()?.querySelector(`[data-apcs-identity-label="${k}"]`),v=recordRoot()?.querySelector(`[data-apcs-identity-value="${k}"]`),g=l?.closest('.identityGrid,.recordGrid');const vis=!!l&&!!v&&!!g&&getComputedStyle(g).display!=='none'&&getComputedStyle(g).visibility!=='hidden'&&g.getBoundingClientRect().height>0&&l.getBoundingClientRect().height>0&&v.getBoundingClientRect().height>0;return {label:k,visible:vis,value:(v?.textContent||'').trim()}})};
})();
