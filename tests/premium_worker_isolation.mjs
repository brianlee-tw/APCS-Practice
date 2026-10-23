// Runs the exact operational Worker with a closed in-memory Notion transport.
// No request ever reaches a live Notion database or production Worker.
import worker from '../cloudflare/worker/src/index.mjs';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const REC='36a43be9-58cd-8015-88d3-000ba21d3afc';
const EV='0075c9be-b4d8-41c1-b933-bebd2ccda749';
const SKILL='49e0d7dc-4902-4254-859f-03c617ebb2cf';
const rows=new Map([[REC,[]],[EV,[]]]);const writes=[];let seq=0;
const rt=s=>({rich_text:[{text:{content:s}}]});
const select=s=>({select:{name:s}});
const json=x=>new Response(JSON.stringify(x),{headers:{'Content-Type':'application/json'}});
const pb={id:'3c643be9-58cd-8195-823c-f7af5c9e809e',properties:{
 'Problem ID':rt('ZJ-e339'),'題目':{title:[{text:{content:'Isolation fixture'}}]},
 '來源平台':select('ZeroJudge'),'作答平台':select('ZeroJudge'),
 '題目連結':{url:'https://example.invalid/isolation-fixture'},
 '難度（D1–D5）':select('D2 基礎'),'技能節點':{relation:[{id:'isolated-skill-22'}]}}};
globalThis.fetch=async (url,options={})=>{
 const u=new URL(url);assert.equal(u.origin,'https://api.notion.com');
 const path=u.pathname.replace('/v1','');const body=options.body?JSON.parse(options.body):{};
 if(path===`/pages/${pb.id}`)return json(pb);
 if(path===`/data_sources/${SKILL}/query`)return json({results:[{id:'isolated-skill-22',properties:{'Skill UID':rt('S22_Prefix_Sum')}}]});
 const m=path.match(/^\/data_sources\/([^/]+)\/query$/);
 if(m){assert(rows.has(m[1]));const filter=body.filter;const value=filter.rich_text?.equals;
  return json({results:rows.get(m[1]).filter(p=>p.properties[filter.property]?.rich_text?.[0]?.text?.content===value),has_more:false});}
 if(path==='/pages' && options.method==='POST'){
  const ds=body.parent.data_source_id;assert(rows.has(ds));
  const p={id:'isolated-page-'+(++seq),url:'https://example.invalid/'+seq,properties:body.properties};
  rows.get(ds).push(p);writes.push({data_source:ds,properties:body.properties});return json(p);
 }
 throw new Error('Unmocked transport refused: '+path);
};
const env={NOTION_API_TOKEN:'isolated-not-a-credential',WRITE_KEY:'isolated-local-key',ASSETS:{fetch(){throw Error('No asset/network fallback');}}};
function bundle(id,overrides={}){
 const a={attempt_id:'isolated_attempt_'+id,writeback_id:'isolated_writeback_'+id,pb_uid:'PB-25',problem_id:'ZJ-e339',started_at:null,finished_at:'2026-10-22T08:00:00+08:00',language:'cpp',judge_result:'AC',assistance:'A0',independent:true,attempt_count:1,active_minutes:12,timed:false,novelty:'new',activity:'Core Independent',source:'VS Code Direct',note:'ISOLATED SOFTWARE TEST; not learner evidence',...overrides};
 return {schema_version:'v2.3-remote-writeback-1',writeback_id:a.writeback_id,attempt:a,evidence:[{...a,event_id:a.writeback_id+'.ev1',skill_uid:'S22_Prefix_Sum',track:a.track||'Implementation',outcome:a.outcome||'PASS',occurred_at:a.finished_at}]};
}
async function send(b){const response=await worker.fetch(new Request('https://isolation.invalid/api/record',{method:'POST',headers:{'Content-Type':'application/json','X-APCS-Write-Key':env.WRITE_KEY},body:JSON.stringify(b)}),env);return {status:response.status,body:await response.json()};}
const results=[];
for(const [name,changes] of [
 ['Guided Practice',{activity:'Guided Drill',assistance:'A2',independent:false}],
 ['Core Independent',{}],['Transfer',{activity:'Transfer Challenge',novelty:'transfer'}],
 ['Assisted Debugging',{assistance:'A3',independent:false}],
 ['Delayed Retest',{activity:'Review',novelty:'delayed_retest',note:'ISOLATED fixture; prior occurrence 14 days earlier'}],
 ['Timed Practice',{timed:true}],
 ...['WA','CE','RE','TLE'].map(x=>['Judge '+x,{judge_result:x,outcome:'FAIL'}]),
 ['Reading N/A',{judge_result:'N/A',track:'Reading',outcome:'PARTIAL',independent:null}],
 ['Python Transfer',{language:'python',novelty:'transfer',activity:'Transfer Challenge'}]
]){
 const b=bundle(String(results.length).padStart(3,'0'),changes);const before=writes.length;
 const first=await send(b);assert.equal(first.status,201,JSON.stringify(first));assert.equal(first.body.complete,true);
 const retry=await send(b);assert.equal(retry.status,200,JSON.stringify(retry));assert.equal(writes.length,before+2);
 assert.equal(retry.body.rec.duplicate,true);assert.equal(retry.body.evidence[0].duplicate,true);
 const rec=rows.get(REC).at(-1);const ev=rows.get(EV).at(-1);
 assert.equal(ev.properties['Valid for Gate']?.checkbox??false,false);
 assert.deepEqual(ev.properties.Skill.relation,[{id:'isolated-skill-22'}]);
 assert.deepEqual(ev.properties['Solve Record'].relation,[{id:rec.id}]);
 if(changes.language==='python')assert.equal(rec.properties['使用語言'].multi_select[0].name,'Python');
 if(changes.judge_result==='N/A')assert.equal(rec.properties['最新提交結果'].select.name,'未提交/未知');
 results.push({scenario:name,status:'PASS',new_rec:1,new_ev:1,exact_retry_no_new_writes:true,gate_default:false});
}
const invalid=bundle('mismatch');invalid.evidence[0].assistance='A5';
assert.equal((await send(invalid)).status,400);
results.push({scenario:'Mismatched assistance rejected',status:'PASS'});
assert(writes.every(x=>x.data_source===REC||x.data_source===EV));
assert.equal(writes.filter(x=>x.data_source===SKILL).length,0);
const report={scope:'EXACT_WORKER_WITH_IN_MEMORY_NOTION',production_writes:0,skill_mastery_writes:0,scenarios:results,remote_measurement:'NOT_RUN; Valid for Gate remains false, no automatic RM/IM',formal_reading:'BLOCKED; C-form sealing not established',review_due:'Local adaptive memory covered by Python repository regression; no remote Review Due mutation',language:'REC language preserved; EV has no independent language field, so C++17 mastery is not inferred'};
if(process.argv[2])await fs.writeFile(process.argv[2],JSON.stringify(report,null,2));
console.log(JSON.stringify({status:'PASS',scenarios:results.length,production_writes:0}));
