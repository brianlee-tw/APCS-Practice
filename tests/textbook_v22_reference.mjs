// Paper companion is a reference projection, never a second curriculum or progress source.
import assert from 'node:assert/strict';
import fs from 'node:fs';
const read=p=>JSON.parse(fs.readFileSync(new URL('../'+p,import.meta.url),'utf8'));
const paper=read('docs/textbook-v22/crosswalk.json');
const curriculum=read('curriculum/source.v23.json');
const routes=read('curriculum/lesson_routes.v24.json').routes;
assert.equal(paper.edition,'2.2');
assert.equal(paper.lessons.length,56);
assert.equal(new Set(paper.lessons.map(x=>x['Lesson UID'])).size,56);
const formal=paper.lessons.filter(x=>x['Formal Lesson']);
assert.equal(formal.length,52);
assert.equal(new Set(formal.map(x=>x.Chapter)).size,14);
const skills=new Map(curriculum.skills.map(x=>[x.uid,x]));
assert.equal(skills.size,39);
assert.equal(Object.keys(paper.skill_relevance).length,39);
for(const [uid,relevance] of Object.entries(paper.skill_relevance)){
 assert.deepEqual(relevance,skills.get(uid).relevance,uid+' classification drift');
}
let relations=0;
for(const l of paper.lessons){
 assert(['I','II','III','IV','V'].includes(l.Volume));
 assert(Number.isInteger(l['Paper Local Page']) && l['Paper Local Page']>0);
 assert.equal(new URL(l['Notion Lesson URL']).protocol,'https:');
 if(l['Formal Lesson'])assert.equal(l['Notion Lesson URL'],routes[l['Lesson UID']]);
 for(const skill of l['Skill UID'].split('; ')){assert(skills.has(skill),skill);relations++;}
 if(l['Hosted Workspace URL']!=='NOT PRODUCED')assert.equal(new URL(l['Hosted Workspace URL']).pathname.startsWith('/learn/'),true);
}
assert.equal(relations,71);
const forbidden=['mastery','ready','score','progress','RM','IM','Valid for Gate'];
for(const l of paper.lessons)for(const key of forbidden)assert(!(key in l));
console.log(JSON.stringify({status:'PASS',formal:formal.length,extensions:4,skills:skills.size,relations,role:'reference only; no runtime mutation'}));
