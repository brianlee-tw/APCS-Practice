(()=>{
'use strict';
const C=window.APCS_WORKSPACE_CONFIG||{};
const DATA=window.APCS_WORKSPACE_DATA||[];
const $=q=>document.querySelector(q), $$=q=>[...document.querySelectorAll(q)];
const esc=x=>String(x??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const roleKey=p=>String(p?.roleKey||p?.role||'guided').toLowerCase().replace(/[^a-z]/g,'');
const coreLike=p=>['core','transfer'].includes(roleKey(p));
const ROLE_POLICY={
 worked:{label:'Worked Example',timerMode:'learn',guidance:[
   ['學習目標','先理解範例中的 representation、invariant 與推導，再嘗試自己重建。'],
   ['操作方式','允許逐步展開答案、trace 與完整 reference；重點不是限時 AC。'],
   ['完成標準','最後應能關掉範例，自己重新說明核心推導與實作骨架。']
 ],evidence:'Worked Example 主要形成理解與重建證據，不應被當作獨立解題 Gate。'},
 guided:{label:'Guided Drill',timerMode:'scaffold',guidance:[
   ['學習目標','先把模型走對，再逐步降低支架；一次 AC 不是唯一目標。'],
   ['操作方式','先完成短暫 A0 嘗試，之後可依需要按 A1 → A2 → A3 → A4 逐層拿提示。'],
   ['完成標準','能在提示逐步撤除後，自己完成核心步驟並說明為什麼。']
 ],evidence:'Guided Drill 可形成學習 Evidence；若 Assistance 很高，不能把該次當作 independent candidate。'},
 core:{label:'Core Independent',timerMode:'independent',guidance:[
   ['學習目標','驗證你能否依 constraints、representation 與已學模型自主完成。'],
   ['操作方式','先保留完整 A0 獨立作答窗，不因焦慮過早打開提示。'],
   ['完成標準','若要支援 independent candidate，優先 A0；A1 尚可保留部分候選，A2+ 不再視為獨立 Gate。']
 ],evidence:'Core Independent 的 Evidence 只有在 Assistance、Independent 與真實 attempt facts 都成立時才可能成為 Gate candidate。'},
 transfer:{label:'Transfer Challenge',timerMode:'transfer',guidance:[
   ['學習目標','辨識哪些 constraints、representation 或 invariant 能從已學內容遷移到陌生題。'],
   ['操作方式','先保留陌生題辨識時間；A1 只做最小診斷，不提前揭露關鍵 observation。'],
   ['完成標準','除了做對，還要能說明哪些條件讓舊方法仍成立、哪些條件一改就必須換方法。']
 ],evidence:'Transfer Challenge 若要支援較高 transfer candidate，需 meaningful transfer 且 Assistance 維持 A0–A1。'},
 mock:{label:'Mock',timerMode:'mock',guidance:[
   ['學習目標','模擬正式測驗環境，測的是在沒有提示的情況下能否自行完成。'],
   ['操作方式','作答期間 AI Coach 鎖定；結束 attempt 後才進入 debug / solution / debrief。'],
   ['完成標準','以真實時間、提交結果與完整獨立過程為主；不要把練習支架帶進模考。']
 ],evidence:'Mock 的價值在於無提示、限時、完整作答情境。'}
};
const RP=()=>ROLE_POLICY[roleKey(P())]||ROLE_POLICY.guided;
const RESULT_META=[['未提交/未知','No Judge'],['AC','Accepted'],['WA','Wrong Answer'],['CE','Compile Error'],['RE','Runtime Error'],['TLE','Time Limit']];
const ASSIST_META=[['A0','完全獨立','沒有拿任何提示','green'],['A1','只有診斷','只確認我卡在哪裡','cyan'],['A2','概念提示','得到性質、定義或觀念提醒','blue'],['A3','方向提示','得到解題方向或關鍵表示法','amber'],['A4','骨架提示','看到 pseudocode、步驟或程式骨架','orange'],['A5','完整參考','看過完整解法或 reference code','red']];
const ASSIST_HELP=Object.fromEntries(ASSIST_META.map(x=>[x[0],x[1]+' · '+x[2]]));
const STAGE_META=[['第一次接觸','初次','第一次做這個題型'],['理解觀念','理解','正在把模型弄懂'],['獨立解題','獨立','用已學知識自己完成'],['限時實戰','限時','有明確時間壓力'],['複習驗證','複習','隔一段時間重新驗證']];
const ERR_META=[['讀題','題意或條件理解','cyan'],['演算法','方法選擇或推導','violet'],['資料結構','容器或狀態設計','blue'],['邊界條件','index / range / corner case','orange'],['複雜度','時間或空間超標','amber'],['實作Bug','流程、狀態或更新錯誤','red'],['語法','編譯與 C++ 語法','pink']];
let cur=0,elapsed=0,running=false,tick=null,attemptStarted=false;
let assist='',ind='',stage='第一次接觸',errors=[],scaffoldLevel=0,evidenceNotes={},audit=[],result='未提交/未知',reviewTouched=false,recordSaved=false;

const P=()=>DATA[cur]||DATA[0];
const k=()=>`${C.ns||'apcs-workspace-'}${P().pb}`;
function read(){try{return JSON.parse(localStorage.getItem(k())||'{}')}catch{return {}}}
function writeObj(o){localStorage.setItem(k(),JSON.stringify(o))}
function formatClock(sec){sec=Math.max(0,Math.floor(sec));return `${String(Math.floor(sec/60)).padStart(2,'0')}:${String(sec%60).padStart(2,'0')}`}
function writebackId(){const o=read();if(o.writebackId)return o.writebackId;const id=`ui5134-${String(P().pb).toLowerCase()}-${crypto.randomUUID()}`;o.writebackId=id;writeObj(o);return id}
function checkedAudit(){return $$('[data-audit]').filter(x=>x.checked).map(x=>Number(x.dataset.audit))}
function state(){return {
 elapsed,attemptStarted,assist,ind,stage,errors,scaffoldLevel,evidenceNotes,audit:checkedAudit(),recordSaved,
 plan:$('#planText')?.value||'',result:resultValue(),att:$('#att')?.value||1,mins:$('#mins')?.value||0,
 review:$('#review')?.value||'',take:$('#take')?.value||'',writebackId:writebackId()
}}
function stamp(){try{return new Intl.DateTimeFormat('zh-TW',{hour:'2-digit',minute:'2-digit',hour12:true}).format(new Date())}catch{return new Date().toLocaleTimeString()}}
function save(silent=false){writeObj(state());const d=$('#draftState');if(d)d.textContent=`草稿已儲存 · ${stamp()}`;if(!silent){updateErrorUI();updateTakeQuality();renderGate()}}
function restore(){const o=read();elapsed=Number(o.elapsed)||0;attemptStarted=!!o.attemptStarted;assist=o.assist||'';ind=o.ind??'';stage=o.stage||'第一次接觸';errors=Array.isArray(o.errors)?o.errors:[];scaffoldLevel=Number(o.scaffoldLevel)||0;evidenceNotes=o.evidenceNotes||{};audit=Array.isArray(o.audit)?o.audit:[];result=o.result||'未提交/未知';recordSaved=!!o.recordSaved;if($('#planText'))$('#planText').value=o.plan||'';if($('#att'))$('#att').value=o.att||1;if($('#mins'))$('#mins').value=o.mins||0;if($('#review'))$('#review').value=o.review||'';if($('#take'))$('#take').value=o.take||''}
function requireCanonicalDom(){
 const ids=['timerMeta','ring','pct','clock','remaining','phase','laneFill','laneMarkers','timerMilestones','start','reset','syncTimer','judge',
 'goal','startQ','startAnswer','roleGuidance','known','blocked','wins','chevronFlow','planText','planSt','checkGrid',
 'recordPreview','identityGrid','roleEvidence','resultChoices','assist','assistChoices','ind','indChoices','stage','stageChoices','attMinus','att','attPlus','minMinus','mins','minPlus','syncTimer2','errorCount','clearErrors','errs','review','take','gate','submitRec','recSt','endpointState','writeKey','saveEndpoint','clearEndpoint','draftState','systemState'];
 const missing=ids.filter(id=>!document.getElementById(id));
 if(missing.length)throw new Error('CANONICAL_SLOT_MISSING:'+missing.join(','));
}
function roleRule(p){
 const r=roleKey(p);
 if(r==='worked')return '先預測，再查看逐步示範；看完後關閉參考內容，重新用自己的步驟完成一次。';
 if(r==='guided')return '先自己做第一版；卡住時再依序取得診斷、表示、規劃與實作提示，每次只開需要的一層。';
 if(r==='core')return '先保留完整獨立作答時間；需要提示時從最低層級開始，使用 A2 以上會記為非獨立完成。';
 if(r==='transfer')return '先從限制、資料關係與不變量自己辨認切入點；題前不直接揭露關鍵方法。';
 return '正式作答期間不開提示或解答；提交後再進入除錯與整理。'
}
function timerProfile(p){
 const r=roleKey(p),a0=Math.max(0,Number(p.a0)||0),lim=Math.max(1,Number(p.limit)||15);
 if(r==='worked')return {chip:'學習節奏',markers:[
   {pct:25,short:'觀察',desc:'先看 representation'},
   {pct:55,short:'推導',desc:'每步先預測'},
   {pct:85,short:'重建',desc:'關掉 reference'},
   {pct:100,short:'整理',desc:'壓縮 mental model'}
 ],phase:m=>m<lim*.3?'觀察表示法與關鍵狀態。':m<lim*.65?'跟著推導，但每一步先自己預測。':m<lim?'關掉 reference，嘗試自己重建。':'整理最短 mental model。'};
 if(r==='guided')return {chip:`A0 ${a0}m • ${lim}m`,markers:[
   {pct:Math.max(8,Math.min(60,a0/lim*100)),short:'A0',desc:`獨立 ${a0}m`},
   {pct:55,short:'A1/A2',desc:'低階提示可用'},
   {pct:80,short:'A3/A4',desc:'仍卡住才升級'},
   {pct:100,short:'上限',desc:`${lim}m 收斂`}
 ],phase:m=>m<a0?'保持 A0：先說出模型再寫 code。':m<lim*.8?'真的卡住才拿 A1 / A2。':m<lim?'仍卡住再考慮 A3 / A4。':'到首次上限：先整理卡點。'};
 if(r==='core')return {chip:`A0 ${a0}m • ${lim}m`,markers:[
   {pct:Math.max(8,Math.min(70,a0/lim*100)),short:'A0',desc:`完整獨立 ${a0}m`},
   {pct:70,short:'A1',desc:'只做診斷'},
   {pct:100,short:'上限',desc:`${lim}m 收斂`}
 ],phase:m=>m<a0?'完整 A0 獨立窗：先不要拿提示。':m<lim?'需要時只拿 A1 診斷。':'到首次上限：先記錄卡點再決定下一步。'};
 if(r==='transfer')return {chip:`A0 ${a0}m • ${lim}m`,markers:[
   {pct:Math.max(8,Math.min(70,a0/lim*100)),short:'辨識',desc:'先找 constraints'},
   {pct:75,short:'最小提示',desc:'避免破壞遷移'},
   {pct:100,short:'上限',desc:`${lim}m 收斂`}
 ],phase:m=>m<a0?'先辨識 constraints / representation。':m<lim?'只拿最小提示，保留遷移判斷。':'到首次上限：寫下判斷依據。'};
 return {chip:'正式模考',markers:[{pct:50,short:'50%',desc:'時間過半'},{pct:80,short:'80%',desc:'最後 20%'},{pct:100,short:'到時',desc:'結束 attempt'}],phase:m=>m<lim*.5?'模考進行中：AI Coach 鎖定。':m<lim*.8?'時間過半：檢查是否卡太久。':m<lim?'最後 20%：整理可拿分部分。':'時間到：結束 attempt 後再檢討。'}
}
function renderMilestones(){
 const p=P(),tp=timerProfile(p);
 $('#timerMeta').textContent=tp.chip;
 $('#laneMarkers').innerHTML=tp.markers.map(x=>`<div class="mk" style="left:${Math.min(100,x.pct)}%"><i></i><span>${esc(x.short)}</span></div>`).join('');
 $('#timerMilestones').innerHTML=tp.markers.map(x=>`<div class="timerMilestone"><b>${esc(x.short)}</b><span>${esc(x.desc)}</span></div>`).join('')
}
function clock(){
 const p=P(),lim=Math.max(1,Number(p.limit)||15),m=elapsed/60,q=Math.min(150,Math.round(elapsed/(lim*60)*100)),tp=timerProfile(p);
 $('#clock').textContent=formatClock(elapsed);$('#pct').textContent=Math.min(999,q)+'%';$('#ring').style.setProperty('--q',Math.min(100,q));$('#laneFill').style.width=Math.min(100,q)+'%';
 const diff=lim*60-elapsed,rem=$('#remaining');if(diff>=0){rem.className='remaining';rem.textContent='剩餘 '+formatClock(diff)}else{rem.className='remaining over';rem.textContent='超時 +'+formatClock(-diff)}
 $('#phase').textContent=tp.phase(m);
 if(document.activeElement!==$('#mins'))$('#mins').value=(Math.round(m*10)/10).toString()
}
function startTimer(){attemptStarted=true;if(running){clearInterval(tick);running=false;$('#start').textContent='繼續';save(true);return}running=true;$('#start').textContent='暫停';tick=setInterval(()=>{elapsed++;clock();if(elapsed%5===0)save(true)},1000);save(true)}
function resetTimer(){clearInterval(tick);running=false;elapsed=0;$('#start').textContent='開始';clock();save(true)}
function judgeInfo(p){
 const raw=String(p.judge||p.source||'').trim(),custom=/custom|apcs/i.test(raw)||String(p.id||'').startsWith('CUSTOM-');
 if(custom)return {href:`/tools/custom-oj?pb=${encodeURIComponent(p.pb)}`,text:'在 APCS OJ 開啟題目 ↗',source:'APCS Custom OJ'};
 const name=raw||'OJ';return {href:p.url||'#',text:`開啟 ${name} 題目 ↗`,source:p.source||name}
}
function renderFacts(){
 const p=P(),rp=RP(),j=judgeInfo(p),skill=p.targetSkills||C.skill||'—';
 $('#facts').innerHTML=[['難度',p.d||'—','difficulty'],['角色',rp.label,'role'],['Skill',skill,'skill'],['時間',`${p.limit||'—'} min`,'time'],['OJ',j.source,'oj']]
 .map(([k,v,c])=>`<div class="factCard ${c}"><span>${esc(k)}</span><b>${esc(v)}</b></div>`).join('');
 $('#judge').href=j.href;$('#judge').textContent=j.text
}
function doneCaption(p,i){
 const arr=Array.isArray(p.done)&&p.done.length?p.done:[];
 return arr[i]?.body||'留下能在下一題重用的可檢查產物。'
}
function renderWorkedWalkthrough(){
 const p=P(),box=$('#workedWalkthrough');if(!box)return;box.innerHTML='';
 if(roleKey(p)!=='worked')return;
 const steps=Array.isArray(p.workedSteps)?p.workedSteps.slice(0,6):[];
 if(!steps.length)return;
 box.innerHTML=`<div class="workedBox"><h4>Worked Example</h4><p class="small">先完成 Prediction，再看逐步示範；看完後關閉 reference 並從空白重建。</p><textarea id="workedPrediction" placeholder="先寫下你的預測與理由；至少一句。"></textarea><div class="row" style="margin-top:9px"><button class="btn primary" id="workedReveal" type="button">顯示逐步 walkthrough</button><button class="btn" id="workedHide" type="button" style="display:none">隱藏 reference，開始重建</button></div><div id="workedBody" style="display:none"></div></div>`;
 const pred=$('#workedPrediction'),body=$('#workedBody'),reveal=$('#workedReveal'),hide=$('#workedHide');
 reveal.onclick=()=>{if(!pred.value.trim()){toast('先做 Prediction','Worked Example 仍要求 prediction-before-reveal。');return}attemptStarted=true;markAssistAtLeast('A0');body.style.display='block';body.innerHTML=`<div class="workedSteps">${steps.map((x,i)=>{const a=Array.isArray(x)?x:[x.title,x.body];return `<div class="workedStep"><b>0${i+1} · ${esc(a[0]||'步驟')}</b><span>${esc(a[1]||'')}</span></div>`}).join('')}</div><h4 style="margin-top:14px">Reference</h4><pre class="workedRef">${esc(p.workedRef||'')}</pre><div class="phaseNote">${esc(p.reconstruct||'隱藏 reference 後重新完成一次。')}</div>`;hide.style.display='inline-flex';reveal.style.display='none';save(true)};
 hide.onclick=()=>{body.style.display='none';hide.style.display='none';reveal.style.display='inline-flex';toast('Reference 已隱藏','現在請從空白重建，再回來 compare。')}
}
function renderTask(){
 const p=P(),rp=RP();
 $('#goal').textContent=p.goal||p.summary||'完成本題需要的 representation、reasoning 與 verification。';
 $('#startQ').textContent=p.startQuestion||'先寫下你會如何表示問題，再決定第一個可驗證步驟。';
 $('#startAnswer').textContent=p.startAnswer||'先保留自己的回答；真的需要時再展開。';
 $('#known').innerHTML=(p.known||C.known||[]).map(x=>`<span class="tag can">${esc(x)}</span>`).join('');
 $('#blocked').innerHTML=(p.blocked||C.blocked||[]).map(x=>`<span class="tag block">${esc(x)}</span>`).join('');
 $('#roleGuidance').innerHTML=(p.taskMeta||rp.guidance).slice(0,3).map((x,i)=>`<div class="roleNotice"><div class="icon">0${i+1}</div><div><b>${esc(x.title||x[0])}</b><p>${esc(x.body||x[1])}</p></div></div>`).join('');
 renderWorkedWalkthrough();
 const done=(p.done||[]).slice(0,3);$('#wins').innerHTML=done.map((x,i)=>`<div class="doneItem"><i>0${i+1}</i><b>${esc(x.title||x)}</b><span>${esc(x.body||doneCaption(p,i))}</span></div>`).join('');
 const board=$('#known')?.closest('.card');const skillNode=board?.querySelector('.small b');if(skillNode)skillNode.textContent=C.skill||p.targetSkills||'';
 const labEye=[...$$('#task .eyebrow')].find(x=>/High-leverage Labs/i.test(x.textContent||''));const labBox=labEye?.nextElementSibling;
 if(labBox&&Array.isArray(C.labLinks)){labBox.innerHTML=C.labLinks.map(x=>`<a class="btn" href="${esc(x.href)}" target="_blank" rel="noopener">${esc(x.label)} ↗</a>`).join('');if(labEye.parentElement)labEye.parentElement.hidden=C.labLinks.length===0}
 const details=$('#task details.preDetails,#task details.answerOnly');if(details&&!details.dataset.apcsBound){details.dataset.apcsBound='1';details.addEventListener('toggle',()=>{if(details.open){const r=roleKey(P());if(r==='worked')markAssistAtLeast('A0');else if(r==='guided')markAssistAtLeast('A1');else if(coreLike(P()))markAssistAtLeast('A2')}})}
}
function renderPlan(){
 const p=P(),steps=(p.planSteps||[]).slice(0,4),items=(p.checks||[]).slice(0,5);
 $('#chevronFlow').innerHTML=steps.map((x,i)=>`<div class="chev"><span class="no">0${i+1}</span><h4>${esc(x.title||x[0]||x)}</h4><p>${esc(x.body||x[1]||'')}</p></div>`).join('');
 $('#planText').placeholder=p.planPlaceholder||'先寫 representation / candidate / state / invariant，再寫 boundary tests 與 implementation plan。';
 $('#checkGrid').innerHTML=items.map((x,i)=>`<span class="checkTile"><input type="checkbox" id="ck-${esc(P().pb)}-${i}" data-audit="${i}" ${audit.includes(i)?'checked':''}><label for="ck-${esc(P().pb)}-${i}"><b>${esc(x.title||x[0]||'檢查')}</b><span>${esc(x.body||x[1]||'')}</span></label></span>`).join('');
 $$('[data-audit]').forEach(x=>x.onchange=()=>{audit=checkedAudit();attemptStarted=true;save()});
 const st=$('#planSt');if(st)st.textContent=($('#planText').value||'').trim()?'草稿已保存在本機':'本機草稿尚未修改';
 const legacyAudit=$('#auditProgress');if(legacyAudit)legacyAudit.hidden=true;
 const legacyFinish=$('#finishAttempt');if(legacyFinish)legacyFinish.hidden=true
}
function renderProblemSelection(){
 $$('.problemBtn').forEach((b,i)=>{const on=i===cur;b.classList.toggle('on',on);b.style.borderColor='';b.style.background='';if(on&&roleKey(P())==='guided'){b.style.borderColor='color-mix(in srgb,var(--orange) 45%,var(--line))';b.style.background='linear-gradient(145deg,rgba(255,153,102,.14),rgba(255,136,198,.06))'}})
}
function resultValue(){return document.querySelector('input[name="result"]:checked')?.value||result||'未提交/未知'}
function renderResults(){
 const curv=result||'未提交/未知';
 $('#resultChoices').innerHTML=RESULT_META.map(([v,d],i)=>`<span class="choice" data-v="${esc(v)}"><input type="radio" name="result" id="r${i}" value="${esc(v)}" ${curv===v?'checked':''}><label for="r${i}"><b>${esc(v)}</b><span>${esc(d)}</span></label></span>`).join('');
 $$('input[name=result]').forEach(x=>x.onchange=()=>{result=x.value;save()})
}
function renderAssist(){
 $('#assist').value=assist;
 $('#assistChoices').innerHTML=ASSIST_META.map(([code,name,desc,tone],i)=>`<span class="assistChoice" style="--pick:var(--${tone})"><input type="radio" name="assistChoice" id="as${i}" value="${code}" ${assist===code?'checked':''}><label for="as${i}"><div class="choiceCode">${code}</div><div class="choiceName">${esc(name)}</div></label></span>`).join('');
 $$('input[name=assistChoice]').forEach(x=>x.onchange=()=>{assist=x.value;$('#assist').value=assist;if(coreLike(P())&&['A2','A3','A4','A5'].includes(assist))ind='false';renderIndependent();save()});
 const help=$('#assistHelp');if(help)help.textContent=assist?ASSIST_HELP[assist]:'請先選擇一項。'
}
function renderIndependent(){
 $('#ind').value=ind;
 const arr=[['true','是，主要由我完成','核心思路與實作主要由我完成','green'],['false','否，本次有實質協助','有人或 AI 實質參與關鍵思路 / 實作','amber']];
 $('#indChoices').innerHTML=arr.map(([v,n,d,t],i)=>`<span class="binaryChoice" style="--pick:var(--${t})"><input type="radio" name="indChoice" id="in${i}" value="${v}" ${ind===v?'checked':''}><label for="in${i}"><div class="choiceName">${esc(n)}</div><div class="choiceHelp">${esc(d)}</div></label></span>`).join('');
 $$('input[name=indChoice]').forEach(x=>x.onchange=()=>{ind=x.value;$('#ind').value=ind;save()})
}
function renderStage(){
 $('#stage').value=stage;
 $('#stageChoices').innerHTML=STAGE_META.map(([v,n,d],i)=>`<span class="stageChoice" style="--pick:var(--${['cyan','blue','green','orange','violet'][i]})"><input type="radio" name="stageChoice" id="st${i}" value="${esc(v)}" ${stage===v?'checked':''}><label for="st${i}"><div class="choiceCode">0${i+1}</div><div class="choiceName">${esc(n)}</div><div class="choiceHelp">${esc(d)}</div></label></span>`).join('');
 $$('input[name=stageChoice]').forEach(x=>x.onchange=()=>{stage=x.value;$('#stage').value=stage;save()})
}
function renderErrors(){
 $('#errs').innerHTML=ERR_META.map(([name,desc,tone],i)=>`<span class="errChip" style="--err:var(--${tone})"><input type="checkbox" id="e${i}" value="${esc(name)}" ${errors.includes(name)?'checked':''}><label for="e${i}"><b>${esc(name)}</b><span>${esc(desc)}</span></label></span>`).join('');
 $('#errs').onchange=()=>{errors=$$('#errs input:checked').map(x=>x.value);save()};updateErrorUI()
}
function updateErrorUI(){
 const count=$$('#errs input:checked').length;$('#errorCount').textContent=`${count} 已選`;
 const box=$('#errorSuggest');if(!box)return;
 const r=resultValue();let t='先標記第一個 root cause；可複選，但不要把所有後續症狀都當成獨立錯誤。';
 if(r==='WA')t='WA：先區分讀題、方法、邊界與實作，找最早的錯誤原因。';
 if(r==='TLE')t='TLE：回到 operation count 與 constraints，不要只做常數微調。';
 if(r==='RE')t='RE：先檢查非法 index、boundary 與 state 第一次失效的位置。';
 if(r==='CE')t='CE：先修語法，再回到原本 reasoning；編譯成功不等於解題完成。';
 box.textContent=t
}
function recommendation(){
 let days=3,reason='';const r=resultValue();
 if(r==='AC'){if(assist==='A0'&&ind==='true'){days=stage==='複習驗證'?14:7;reason='低 Assistance 且獨立完成：拉開間隔做 delayed verification。'}else if(['A1','A2'].includes(assist)){days=3;reason='已完成但仍有低階提示：縮短間隔確認支架能否撤掉。'}else{days=1;reason='Assistance 偏高：隔天重做，避免只記住剛看過的解法。'}}
 else if(r==='未提交/未知'){days=1;reason='尚未有穩定提交結果：24 小時內回來完成。'}else{days=1;reason='本次未通過：隔天優先修正第一個 root cause。'}
 if(roleKey(P())==='worked'&&r==='AC')reason='Worked Example：複習重點是關掉 reference 後重建。';
 if(roleKey(P())==='transfer'&&r==='AC'&&assist==='A0'&&ind==='true'){days=10;reason='Transfer 在 A0 獨立完成：隔更久並換外觀題驗證遷移。'}
 return {days,reason}
}
function applyReviewRecommendation(){
 const box=$('#reviewRec'),quick=$('#reviewQuick');if(!box||!quick)return;const rec=recommendation();
 box.innerHTML=`<b>系統推薦：${rec.days} 天後複習</b><div>${esc(rec.reason)}</div>`;
 quick.innerHTML=[1,3,7,14].map(d=>`<button data-review="${d}" type="button">+${d} 天</button>`).join('')+'<button data-review="0" type="button">清除</button><button id="applyReviewRec" type="button">採用推薦</button>';
 $$('[data-review]').forEach(b=>b.onclick=()=>{reviewTouched=true;const days=Number(b.dataset.review);if(days===0)$('#review').value='';else{const d=new Date();d.setDate(d.getDate()+days);$('#review').value=d.toISOString().slice(0,10)}save()});
 const a=$('#applyReviewRec');if(a)a.onclick=()=>{reviewTouched=true;const d=new Date();d.setDate(d.getDate()+rec.days);$('#review').value=d.toISOString().slice(0,10);save();toast('已採用複習建議',`${rec.days} 天後`)}
}
function updateTakeQuality(){
 const v=$('#take')?.value.trim()||'',n=v.length,q=$('#takeQuality'),c=$('#takeCount');if(c)c.textContent=`${n} 字`;if(q){q.className='quality '+(n>=24?'good':n>0?'warn':'');q.textContent=n>=24?'可作為未來複習提醒':n>0?'再具體一點會更有用':'建議寫成未來可直接用的提醒'}
}
function renderRecord(){
 const p=P(),rp=RP(),j=judgeInfo(p);
 $('#recordPreview').textContent=`${p.id||p.pb}｜${p.title}`;
 $('#identityGrid').innerHTML=[['PB UID',p.pb],['Problem ID',p.id||'—'],['Difficulty',p.d||'—'],['Role',rp.label],['Source',j.source]].map(([a,b])=>`<div class="identityCell"><span>${esc(a)}</span><b>${esc(b)}</b></div>`).join('');
 $('#roleEvidence').innerHTML=`<b>${esc(p.recordEvidenceTitle||`${rp.label} · Evidence interpretation`)}</b><span>${esc(p.recordEvidenceBody||rp.evidence)}</span>`;
 renderResults();renderAssist();renderIndependent();renderStage();renderErrors();applyReviewRecommendation();updateEndpoint();updateTakeQuality();renderGate()
}
function renderGate(){
 const miss=[];if(resultValue()==='未提交/未知')miss.push('Result');if(!assist)miss.push('Highest Assistance');if(ind==='')miss.push('Independent?');if(!stage)miss.push('Stage');if(coreLike(P())&&['A2','A3','A4','A5'].includes(assist)&&ind!=='false')miss.push('A2+ requires independent=false');if(($('#take')?.value||'').trim().length<8)miss.push('核心收穫至少 8 字');
 $('#gate').innerHTML=miss.length?`<div class="gateRow bad"><span class="gateDot"></span><b>尚未可提交：</b> ${esc(miss.join(' · '))}</div>`:'<div class="gateRow good"><span class="gateDot"></span><b>Record facts 已明確確認。</b></div>';
 $('#submitRec').disabled=miss.length>0||!writeKey()
}
function writeKey(){return (localStorage.getItem('apcs-rec-write-key')||'').trim()}
function updateEndpoint(){const ready=writeKey().length>=24;$('#writeKey').value=writeKey();$('#endpointState').innerHTML=ready?'<span class="endpointBadge"><span class="liveDot"></span><span class="success">Direct Write ready</span></span>':'<span class="endpointBadge"><span class="liveDot" style="background:var(--amber)"></span><span class="pending">需要設定 Write Key</span></span>';renderGate()}
async function submitRecord(){
 renderGate();if($('#submitRec').disabled)return;const body={pb_uid:P().pb,writeback_id:writebackId(),latest_result:resultValue(),assistance:assist,independent:ind==='true',attempts:Math.max(1,Number($('#att').value)||1),time_min:Math.max(0,Number($('#mins').value)||0),stage,error_types:errors,review_date:$('#review').value||'',core_takeaway:$('#take').value.trim()};
 $('#recSt').textContent='寫入中…';try{const r=await fetch('/api/record',{method:'POST',headers:{'Content-Type':'application/json','X-APCS-Write-Key':writeKey()},body:JSON.stringify(body)});const j=await r.json().catch(()=>({}));if(!r.ok||!j.ok)throw new Error(j.error||`HTTP ${r.status}`);recordSaved=true;save(true);$('#recSt').textContent=j.duplicate?'已存在相同 Writeback ID；未建立重複紀錄。':`REC-v3.1 寫入成功${j.rec_uid?' · '+j.rec_uid:''}`}catch(e){$('#recSt').textContent=`寫入失敗：${e.message}`}
}
function markAssistAtLeast(code){const order=['A0','A1','A2','A3','A4','A5'];if(order.indexOf(code)>order.indexOf(assist||'A0'))assist=code;if(coreLike(P())&&['A2','A3','A4','A5'].includes(assist))ind='false';renderAssist();renderIndependent();save(true)}
function nextScaffold(){
 const arr=Array.isArray(P().scaffolds)&&P().scaffolds.length?P().scaffolds:(P().planSteps||[]).map(x=>x.body||x[1]).filter(Boolean);
 if(!attemptStarted&&roleKey(P())!=='worked')return {ok:false,msg:'先開始自己的 attempt，保留 clean A0。'};
 scaffoldLevel=Math.min(4,scaffoldLevel+1);const level='A'+scaffoldLevel,txt=arr[scaffoldLevel-1]||arr[arr.length-1]||'先說明 representation / state 的語意。';markAssistAtLeast(level);return {ok:true,level,text:txt}
}
function coachAllowed(mode){
 const r=roleKey(P());if(mode==='problem'||mode==='record')return {ok:true};if(r==='mock'&&!postAttemptAllowed())return {ok:false,msg:'Mock attempt 尚未完成。'};if(coreLike(P())&&!attemptStarted&&['hint','debug','solution'].includes(mode))return {ok:false,msg:'先開始 clean A0 attempt。'};return {ok:true}
}
function coachPrompt(mode){return `/${mode}\n\n[CONTEXT]\nunit: ${C.unit}\nlesson: ${C.lesson}\ntarget_skill: ${C.skill}\nknown: ${(P().known||C.known||[]).join('; ')}\nnot_yet_learned: ${(P().blocked||C.blocked||[]).join('; ')}\nrole: ${RP().label}\nassistance_so_far: ${assist||'A0'}\n[/CONTEXT]\n\n[PROBLEM]\npb_uid: ${P().pb}\nproblem_id: ${P().id||''}\ntitle: ${P().title}\njudge: ${P().judge||'Custom'}\n[/PROBLEM]\n\n[ROLE_CONTRACT]\n${roleRule(P())}\n[/ROLE_CONTRACT]`}
async function coach(mode){
 const a=coachAllowed(mode);if(!a.ok){$('#copySt').textContent=a.msg;return}
 if(mode==='hint'){const h=nextScaffold();if(!h.ok){$('#copySt').textContent=h.msg;return}const sb=$('#scaffoldBox');if(sb){sb.style.display='block';sb.innerHTML=`<b>${h.level}</b><p>${esc(h.text)}</p>`}}
 if(mode==='debug')markAssistAtLeast('A1');if(mode==='solution')markAssistAtLeast('A5');
 const t=coachPrompt(mode);if($('#promptPreview'))$('#promptPreview').textContent=t;try{await navigator.clipboard.writeText(t);$('#copySt').textContent=`已複製 /${mode} 指令。`}catch{$('#copySt').textContent='已產生 context；瀏覽器未允許自動複製。'}save(true)
}
function renderCoach(){
 $('#coachUse').textContent=P().coachUse||RP().guidance[1][1];
 $$('.modeCard').forEach(b=>{const a=coachAllowed(b.dataset.m);b.classList.toggle('locked',!a.ok);const m=b.querySelector('.lockMsg');if(m)m.textContent=a.ok?'':a.msg})
}
function postAttemptAllowed(){
 if(roleKey(P())==='worked')return true;
 if(resultValue()!=='未提交/未知')return true;
 const total=$$('[data-audit]').length,done=$$('[data-audit]:checked').length,plan=($('#planText')?.value||'').trim();
 return elapsed>0&&plan.length>=8&&total>0&&done===total
}
function renderDebrief(tab='trigger'){
 if(!postAttemptAllowed()){$('#debody').innerHTML='<div class="protectedMsg">先開始真實 attempt、寫下作答規劃並完成提交前檢查，才開放題後整理。</div>';return}
 const d=P().debrief6||{},map={trigger:d.trigger||'回想你最初看到什麼訊號，才決定這樣表示或枚舉。',baseline:d.baseline||P().debrief||P().summary||'把第一版方法與後來修正分開整理。',correctness:d.correctness||'說明為什麼不漏、不重複，以及哪個 invariant / boundary 保證正確。',cpp:d.cpp||'保留一個真正影響實作的 C++ 細節。',pitfalls:d.pitfalls||'記下第一個 root cause、最小反例，以及下一次可更早發現它的方法。',transfer:d.transfer||'寫下一個換題目外觀後仍可沿用的 representation / invariant / testing rule。'};
 $('#debody').innerHTML=`<div class="apcsV4Debrief"><h3>${esc(({trigger:'觸發訊號',baseline:'基準 → 推導',correctness:'正確性',cpp:'C++ 實作',pitfalls:'風險 / 反例',transfer:'測資與遷移'})[tab]||'題後整理')}</h3><p>${esc(map[tab]||map.trigger)}</p></div>`
}
function setSection(id){if(id==='deb'&&!postAttemptAllowed()){toast('Debrief 尚未開放','先開始真實 attempt、完成規劃與提交前檢查。');return}$$('.sec').forEach(x=>x.classList.toggle('on',x.id===id));$$('.navBtn').forEach(x=>x.classList.toggle('on',x.dataset.s===id));if(id==='deb')renderDebrief();if(id==='record')renderRecord()}
function toast(title,body){const t=$('#toast');if(!t)return;$('#toastTitle').textContent=title;$('#toastBody').textContent=body;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2500)}
function render(){
 renderProblemSelection();renderFacts();renderTask();renderPlan();renderCoach();renderDebrief();renderRecord();renderMilestones();clock();
 $('#systemState').textContent=`same-origin · REC-v3.1 · ROUTE-v1 · ${C.lesson}`;
 const setup=$('#record .setupPanel .small');if(setup&&/\/learn\/fnd\//.test(setup.textContent||''))setup.innerHTML=`Workspace 與 API 同源：<code>/learn/${esc(C.route)} → /api/record</code>。Write Key 只存在此瀏覽器 localStorage；Notion API Token 永遠只存在 Cloudflare Secret。`
}
function selectProblem(i){
 save(true);clearInterval(tick);running=false;cur=i;restore();render();$('#start').textContent='開始';const u=new URL(location.href);u.searchParams.set('pb',P().pb);history.replaceState(null,'',u)
}
function bind(){
 $$('.problemBtn').forEach((b,i)=>b.onclick=()=>selectProblem(i));$$('.navBtn').forEach(b=>b.onclick=()=>setSection(b.dataset.s));$$('.modeCard').forEach(b=>b.onclick=()=>coach(b.dataset.m));$$('.tabBtn').forEach(b=>b.onclick=()=>{$$('.tabBtn').forEach(x=>x.classList.toggle('on',x===b));renderDebrief(b.dataset.t)});
 $('#start').onclick=startTimer;$('#reset').onclick=resetTimer;$('#syncTimer').onclick=()=>{$('#mins').value=(Math.round(elapsed/6)/10).toString();save()};$('#syncTimer2').onclick=$('#syncTimer').onclick;
 $('#attMinus').onclick=()=>{$('#att').value=Math.max(1,Number($('#att').value||1)-1);save()};$('#attPlus').onclick=()=>{$('#att').value=Math.min(999,Number($('#att').value||1)+1);save()};$('#minMinus').onclick=()=>{$('#mins').value=Math.max(0,Number($('#mins').value||0)-1).toFixed(1);save()};$('#minPlus').onclick=()=>{$('#mins').value=(Number($('#mins').value||0)+1).toFixed(1);save()};
 $$('[data-min]').forEach(b=>b.onclick=()=>{$('#mins').value=(Number($('#mins').value||0)+Number(b.dataset.min||0)).toFixed(1);save()});
 $('#clearErrors').onclick=()=>{errors=[];renderErrors();save()};
 $('#saveEndpoint').onclick=()=>{const v=$('#writeKey').value.trim();if(v.length<24){toast('Write Key 無效','請使用原本產生的長隨機值。');return}localStorage.setItem('apcs-rec-write-key',v);updateEndpoint();save(true)};$('#clearEndpoint').onclick=()=>{localStorage.removeItem('apcs-rec-write-key');$('#writeKey').value='';updateEndpoint();save(true)};$('#submitRec').onclick=submitRecord;
 $('#planText').oninput=()=>{attemptStarted=true;const s=$('#planSt');if(s)s.textContent='草稿已保存在本機';save()};
 ['att','mins','review','take'].forEach(id=>{const e=$('#'+id);if(e)e.addEventListener('input',()=>{if(id==='review')reviewTouched=true;save()})});
 window.addEventListener('keydown',e=>{if(e.altKey&&/^[1-5]$/.test(e.key)){e.preventDefault();setSection(['task','plan','coach','deb','record'][Number(e.key)-1])}})
}
function qa(){
 return {
  version:document.documentElement.dataset.uiVersion,
  role:roleKey(P()),pb:P().pb,timer:timerProfile(P()),state:state(),
  task:{meta:$$('#roleGuidance .roleNotice').map(x=>x.innerText.trim()),done:$$('#wins .doneItem').map(x=>x.innerText.trim()),known:$$('#known .tag').map(x=>x.textContent.trim()),blocked:$$('#blocked .tag').map(x=>x.textContent.trim())},
  plan:{steps:$$('#chevronFlow .chev').map(x=>({title:x.querySelector('h4')?.textContent||'',body:x.querySelector('p')?.textContent||'',clip:getComputedStyle(x).clipPath})),checks:$$('#checkGrid .checkTile').map(x=>({title:x.querySelector('b')?.textContent||'',body:x.querySelector('label span')?.textContent||''}))},
  record:{results:$$('#resultChoices .choice').map(x=>({title:x.querySelector('b')?.textContent||'',desc:x.querySelector('label span')?.textContent||''})),assist:$$('#assistChoices .assistChoice').map(x=>x.innerText.trim()),ind:$$('#indChoices .binaryChoice').map(x=>x.innerText.trim()),stages:$$('#stageChoices .stageChoice').map(x=>x.innerText.trim()),errors:$$('#errs .errChip').map(x=>x.innerText.trim()),identity:$$('#identityGrid .identityCell').map(x=>({k:x.querySelector('span')?.textContent||'',v:x.querySelector('b')?.textContent||''}))},
  footer:$('#systemState')?.textContent||''
 }
}
const requested=new URL(location.href).searchParams.get('pb'),idx=DATA.findIndex(x=>x.pb===requested);cur=idx>=0?idx:Math.max(0,DATA.findIndex(x=>x.pb===C.def));if(requested&&idx<0&&$('#routeDiagnostic')){$('#routeDiagnostic').style.display='block';$('#routeDiagnostic').textContent=`路徑診斷：${requested} 不屬於 ${C.lesson}；已 fail-closed 到 ${C.def}`}
requireCanonicalDom();restore();bind();render();
window.__APCS_WORKSPACE_V4__={state,selectProblem,recordReady:()=>!$('#submitRec').disabled,timerProfile:()=>timerProfile(P()),postAttemptAllowed,qa,markAssistAtLeast};
})();
