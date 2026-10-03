(()=>{
'use strict';
const C=window.APCS_LAB_CONFIG||{};
const $=q=>document.querySelector(q), $$=q=>[...document.querySelectorAll(q)];
const esc=x=>String(x??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const key=`apcs-lab-v3:${C.slug}`;
let S={predictionDone:false,predictionAttempts:0,firstPrediction:null,operateDone:false,answers:{},step:0,selected:[],picks:{},slider:{},completed:false};
try{S={...S,...JSON.parse(localStorage.getItem(key)||'{}')}}catch{}
const save=()=>localStorage.setItem(key,JSON.stringify(S));
const familyMeta={
  'visualizer':['視覺化探索','拖動控制量，直接看位置或規模如何改變。','cyan'],
  'sequence-simulator':['Sequence Simulator','逐步改變 sequence，觀察 size、index 與內容同步更新。','violet'],
  'trace-player':['Trace Player','逐步前進或回退，找到 state 第一次改變的位置。','violet'],
  'representation-mapper':['Representation Mapper','把來源、目的位置或題意概念配對到正確表示。','cyan'],
  'exit-console':['Exit Console','逐題提交、錯題立即 retry；完成只代表本課主動回憶完成。','green'],
  'contract-lab':['I/O Contract Lab','切換輸入／輸出情境，判斷是否符合 Judge contract。','amber'],
  'coordinate-grid':['Coordinate Grid','直接操作 row / column cell，讓合法座標可見。','cyan'],
  'boundary-simulator':['Boundary Simulator','切換位置並觀察 corner / edge / interior 的合法鄰居。','orange'],
  'testcase-builder':['Testcase Builder','主動組合 boundary cases，檢查 coverage 是否足夠。','green'],
  'state-simulator':['State Simulator','逐步查看 transition 前後的 state 與停止條件。','violet'],
  'ordering-lab':['Transition Order','比較不同 update / check 順序造成的結果。','amber'],
  'budget-meter':['Constraint Budget Meter','調整 constraints，觀察 operation budget 的成長。','orange'],
  'candidate-space':['Candidate Space','把抽象 enumeration 變成可看見的 candidate 數量。','cyan'],
  'oracle-lab':['Baseline Oracle','先算自己的 baseline，再和小型 exhaustive oracle 對照。','green'],
  'compare-board':['Compare Board','把成本或方法並排，依 constraints 比較真正差異。','cyan'],
  'capacity-simulator':['Vector Capacity Simulator','逐次 push，觀察少數 grow event 與 copy cost。','violet'],
  'mistake-replay':['Mistake Replay','重播 expected / actual，停在第一個 divergence。','pink'],
  'trace-builder':['Trace Builder','逐步建立 trace，而不是直接看完成表格。','violet'],
  'counterexample-builder':['Counterexample Builder','選最小 case 挑戰假設或暴露 bug。','orange'],
  'code-reconstruction':['Code Reconstruction','在不看完整答案下補回最小必要 statement。','green'],
  'regression-matrix':['Regression Matrix','把 patch 與 targeted tests 對照，確認修正沒有只通 sample。','green'],
  'claim-board':['Correctness Claim Board','把命題方向、必要／充分與反例放在同一張推理板。','pink'],
  'euclid-visualizer':['Euclid Visualizer','逐步看 a、b、remainder 如何保持 gcd relation。','cyan'],
  'residue-explorer':['Residue Explorer','切換數值與 modulus，直接看餘數類別。','violet']
};
const meta=familyMeta[C.family]||['互動 Lab','操作模型並觀察回饋。','cyan'];
function progress(){const n=(S.predictionDone?1:0)+(S.operateDone?1:0);$('#labProgressText').textContent=`${n}/2`;$('#labProgressFill').style.width=`${n*50}%`;$('#labState').textContent=n===2?'已完成；可以閱讀整理':'先完成判斷，再完成主要互動';$('#debrief').hidden=n<2;S.completed=n===2;save()}
function feedback(el,ok,msg){el.className='labFeedback '+(ok?'good':'bad');el.textContent=msg}
function renderPrediction(){const p=C.predict;if(!p){S.predictionDone=true;return ''}return `<section class="card labPrediction"><div class="labSectionHead"><span class="labStep">先判斷</span><div><h2>${esc(p.q)}</h2><p>先留下自己的選擇，再看局部回饋。</p></div></div><div class="labChoices">${p.options.map((o,i)=>`<button type="button" class="labChoice ${S.predictionDone&&i===p.correct?'correct':''}" data-pred="${i}">${esc(o)}</button>`).join('')}</div><div id="predictionFeedback" class="labFeedback"></div><div class="firstMemory" id="firstPrediction">${S.firstPrediction===null?'第一次選擇尚未記錄':`第一次選擇：${esc(p.options[S.firstPrediction])}`}</div></section>`}
function bindPrediction(){if(!C.predict)return;$$('[data-pred]').forEach(b=>b.onclick=()=>{const i=Number(b.dataset.pred);if(S.firstPrediction===null)S.firstPrediction=i;S.predictionAttempts++;const ok=i===C.predict.correct;if(ok)S.predictionDone=true;feedback($('#predictionFeedback'),ok,ok?`正確。${C.predict.why||''}`:`再想一次。${C.predict.retry||'回到目前 state / boundary 再檢查。'}`);save();renderTop();progress()})}
function opHeader(){return `<div class="familyHead tone-${meta[2]}"><span class="familyBadge">${esc(meta[0])}</span><h2>${esc(C.title)}</h2><p>${esc(meta[1])}</p></div>`}
function renderChoice(op){return `<div class="taskStack">${(op.tasks||[]).map((t,i)=>`<article class="choiceTask"><h3>${i+1}. ${esc(t.q)}</h3><div class="labChoices">${t.options.map((o,j)=>`<button type="button" data-task-answer="${i}:${j}" class="labChoice ${S.answers[i]===j?'picked':''}">${esc(o)}</button>`).join('')}</div><div class="labFeedback" data-task-feedback="${i}"></div></article>`).join('')}</div>`}
function bindChoice(op){$$('[data-task-answer]').forEach(b=>b.onclick=()=>{const [i,j]=b.dataset.taskAnswer.split(':').map(Number),t=op.tasks[i],ok=j===t.correct;S.answers[i]=j;feedback(document.querySelector(`[data-task-feedback="${i}"]`),ok,ok?`正確。${t.why||''}`:`再檢查一次。${t.why? '想想：'+t.why:''}`);if((op.tasks||[]).every((t,k)=>S.answers[k]===t.correct))S.operateDone=true;save();renderTop();progress()})}
function renderSlider(op){for(const c of op.controls||[])if(S.slider[c.id]===undefined)S.slider[c.id]=c.init;const rows=(op.controls||[]).map(c=>`<label class="sliderRow"><span><b>${esc(c.label)}</b><output data-out="${c.id}">${S.slider[c.id]}</output></span><input type="range" min="${c.min}" max="${c.max}" step="${c.step||1}" value="${S.slider[c.id]}" data-slider="${c.id}"></label>`).join('');return `${rows}<div class="metricBoard"><span>${esc(op.metricLabel||'目前結果')}</span><b id="metricValue">—</b><div class="metricBar"><i id="metricFill"></i></div><p>${esc(op.note||'調整控制量並觀察結果。')}</p></div><button class="btn primary" id="confirmOperate" type="button">我已完成觀察</button>`}
function calcSlider(op){const vals=(op.controls||[]).map(c=>Number(S.slider[c.id]));let v=vals[0]||0;if(op.calc==='square')v=(vals[0]||0)*(vals[0]||0)*(vals[1]||1);else if(op.calc==='linear')v=(vals[0]||0)*(vals[1]||1);else if(vals.length>1)v=vals.reduce((a,b)=>a*b,1);$('#metricValue').textContent=Number(v).toLocaleString();$('#metricFill').style.width=Math.min(100,Math.max(6,Math.log10(Math.max(1,v))*15))+'%'}
function bindSlider(op){$$('[data-slider]').forEach(e=>e.oninput=()=>{S.slider[e.dataset.slider]=Number(e.value);document.querySelector(`[data-out="${e.dataset.slider}"]`).textContent=e.value;calcSlider(op);save()});calcSlider(op);$('#confirmOperate').onclick=()=>{S.operateDone=true;save();progress()}}
function renderStepper(op){const states=op.states||[];S.step=Math.min(S.step,Math.max(0,states.length-1));return `<div class="traceStage"><div class="traceIndex">Step ${S.step+1} / ${states.length}</div><pre id="traceState">${esc(states[S.step]||'')}</pre><div class="stepRail">${states.map((_,i)=>`<span class="${i<=S.step?'on':''}"></span>`).join('')}</div><div class="labActions"><button class="btn" id="stepPrev" type="button">← 上一步</button><button class="btn primary" id="stepNext" type="button">下一步 →</button></div></div>`}
function bindStepper(op){const states=op.states||[];$('#stepPrev').onclick=()=>{S.step=Math.max(0,S.step-1);save();renderMain()};$('#stepNext').onclick=()=>{if(S.step<states.length-1)S.step++;if(S.step>=states.length-1)S.operateDone=true;save();renderMain();progress()}}
function renderCases(op){return `<div class="caseGrid">${(op.cases||[]).map((c,i)=>`<button class="caseCard ${S.selected.includes(i)?'on':''}" data-case="${i}" type="button"><b>${esc(c.label)}</b><span>${esc(c.desc||'')}</span></button>`).join('')}</div><div class="coverageBox" id="coverageBox">選擇能真正檢查這個模型的 cases。</div>`}
function bindCases(op){$$('[data-case]').forEach(b=>b.onclick=()=>{const i=Number(b.dataset.case);S.selected=S.selected.includes(i)?S.selected.filter(x=>x!==i):[...S.selected,i];const req=op.required||[];const ok=req.every(x=>S.selected.includes(x));S.operateDone=ok;save();renderMain();progress()})}
function renderMapping(op){return `<div class="mappingBoard">${(op.targets||[]).map((t,i)=>`<div class="mapRow"><b>${esc(t)}</b><div>${(op.sources||[]).map((s,j)=>`<button class="mapChip ${S.picks[i]===j?'on':''}" data-map="${i}:${j}" type="button">${esc(s)}</button>`).join('')}</div></div>`).join('')}</div>`}
function bindMapping(op){$$('[data-map]').forEach(b=>b.onclick=()=>{const [i,j]=b.dataset.map.split(':').map(Number);S.picks[i]=j;S.operateDone=(op.targets||[]).every((_,k)=>S.picks[k]===op.correct[k]);save();renderMain();progress()})}
function renderGrid(op){const selected=new Set(S.selected);return `<div class="coordGrid" style="--cols:${op.cols||4}">${Array.from({length:(op.rows||3)*(op.cols||4)},(_,n)=>{const r=Math.floor(n/(op.cols||4)),c=n%(op.cols||4),id=`${r},${c}`;return `<button data-cell="${id}" class="gridCell ${selected.has(id)?'on':''}" type="button"><b>${r},${c}</b></button>`}).join('')}</div>`}
function bindGrid(op){$$('[data-cell]').forEach(b=>b.onclick=()=>{const id=b.dataset.cell;S.selected=S.selected.includes(id)?S.selected.filter(x=>x!==id):[...S.selected,id];S.operateDone=(op.correct||[]).every(x=>S.selected.includes(x));save();renderMain();progress()})}
function renderOperate(){const op=C.operate||{};let body='';if(op.mode==='choice')body=renderChoice(op);else if(op.mode==='slider')body=renderSlider(op);else if(op.mode==='stepper')body=renderStepper(op);else if(op.mode==='cases')body=renderCases(op);else if(op.mode==='mapping')body=renderMapping(op);else if(op.mode==='grid')body=renderGrid(op);else body='<p>這個 Lab 尚未設定可操作模型。</p>';return `<section class="card familyCard" data-family-panel="${esc(C.family)}">${opHeader()}<div class="familyBody">${body}</div></section>`}
function bindOperate(){const op=C.operate||{};if(op.mode==='choice')bindChoice(op);else if(op.mode==='slider')bindSlider(op);else if(op.mode==='stepper')bindStepper(op);else if(op.mode==='cases')bindCases(op);else if(op.mode==='mapping')bindMapping(op);else if(op.mode==='grid')bindGrid(op)}
function renderTop(){$('#familyName').textContent=meta[0];$('#whyHtml').textContent=C.why_html||'';$('#firstPrediction').textContent=S.firstPrediction===null?'第一次選擇尚未記錄':`第一次選擇：${C.predict?.options?.[S.firstPrediction]??''}`}
function renderMain(){$('#labApp').innerHTML=renderPrediction()+renderOperate();bindPrediction();bindOperate();renderTop();progress()}
function reset(){if(!confirm('重設這個 Lab 的本機進度？'))return;localStorage.removeItem(key);location.reload()}
$('#resetLab').onclick=reset;renderMain();
window.__APCS_LAB_V3__={config:C,state:()=>JSON.parse(JSON.stringify(S)),reset,completeOperation:()=>{S.operateDone=true;save();progress()}};
})();
