import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const file = new URL('../data/free-7day.v1.json', import.meta.url);
const data = JSON.parse(fs.readFileSync(file, 'utf8'));
const errors = [];
const requiredSkills = ['syntax','reading','debug','algorithm','implementation'];
const requiredDayFields = ['day','unitId','title','skill','difficulty','estimatedMinutes','objective','concept','selfCheck','completionRule','nextStep'];

if (data.productId !== 'FREE-7DAY') errors.push('productId must be FREE-7DAY');
if (data.version !== '1.0.0') errors.push('FREE-7DAY version must start at 1.0.0');
if (data.status !== 'available') errors.push('FREE-7DAY canonical content must be available');
if (!Array.isArray(data.days) || data.days.length !== 7) errors.push('FREE-7DAY must contain exactly 7 days');

const ids = new Set();
for (const [idx, day] of (data.days || []).entries()) {
  for (const field of requiredDayFields) if (day[field] === undefined || day[field] === null || day[field] === '') errors.push(`Day ${idx + 1} missing ${field}`);
  if (day.day !== idx + 1) errors.push(`Day sequence mismatch at ${idx + 1}`);
  if (ids.has(day.unitId)) errors.push(`duplicate unitId ${day.unitId}`); ids.add(day.unitId);
  if (!Array.isArray(day.concept) || day.concept.length < 3) errors.push(`${day.unitId} needs >=3 concept points`);
  if (!Array.isArray(day.selfCheck) || day.selfCheck.length < 3) errors.push(`${day.unitId} needs >=3 self-check items`);
  if (!Array.isArray(day.skill) || !day.skill.length || day.skill.some((s) => !requiredSkills.includes(s))) errors.push(`${day.unitId} has invalid skill tags`);
  if (day.day < 7) {
    if (!day.workedExample?.code || !Array.isArray(day.workedExample?.trace)) errors.push(`${day.unitId} missing worked example`);
    if (!day.task?.prompt || !day.task?.solution || !day.task?.explanation) errors.push(`${day.unitId} missing task/solution/explanation`);
    if (!Array.isArray(day.task?.hints) || day.task.hints.length !== 3) errors.push(`${day.unitId} must have exactly 3 Hint Ladder levels`);
    if (!Array.isArray(day.task?.commonMistakes) || day.task.commonMistakes.length < 3) errors.push(`${day.unitId} needs >=3 common mistakes`);
    if (day.task?.choices && (!Number.isInteger(day.task.correctIndex) || day.task.correctIndex < 0 || day.task.correctIndex >= day.task.choices.length)) errors.push(`${day.unitId} invalid correctIndex`);
  }
}

const day7 = data.days?.[6];
const items = day7?.checkpoint?.items || [];
if (items.length !== 5) errors.push('Day 7 checkpoint must contain exactly 5 items');
const checkpointSkills = new Set(items.map((q) => q.dimension));
for (const skill of requiredSkills) if (!checkpointSkills.has(skill)) errors.push(`Day 7 checkpoint missing ${skill}`);
for (const item of items) {
  if (!Array.isArray(item.choices) || item.choices.length !== 4) errors.push(`${item.id} must have four choices`);
  if (!Number.isInteger(item.correctIndex) || item.correctIndex < 0 || item.correctIndex >= item.choices.length) errors.push(`${item.id} invalid correctIndex`);
  if (!item.explanation) errors.push(`${item.id} missing explanation`);
}

const serialized = JSON.stringify(data);
for (const forbidden of ['TODO','TBD','placeholder','lorem ipsum']) if (serialized.toLowerCase().includes(forbidden.toLowerCase())) errors.push(`content contains forbidden placeholder token: ${forbidden}`);

const cpp = String.raw`#include <bits/stdc++.h>
using namespace std;
int firstAtLeast(const vector<int>& a,int target){int l=0,r=(int)a.size()-1;while(l<r){int mid=l+(r-l)/2;if(a[mid]<target)l=mid+1;else r=mid;}return l;}
int main(){
 int score=2;for(int i=1;i<=4;++i){if(i%2==0)score+=i;else score-=1;} if(score!=6) return 1;
 vector<int> v={4,7,1,9};int sum=0;for(int i=0;i<(int)v.size();++i)sum+=v[i];if(sum!=21)return 2;
 vector<int>a={-4,4,8,12,16,20,0};int cnt=0;for(int x:a)if(x>0&&x%4==0&&x%8!=0)++cnt;if(cnt!=3)return 3;
 vector<int>b={3,-1,4,2,5};vector<long long>p(b.size()+1);for(int i=0;i<(int)b.size();++i)p[i+1]=p[i]+b[i];if(p[4]-p[1]!=5)return 4;
 vector<int>c={2,10};if(firstAtLeast(c,10)!=1)return 5;
 vector<int>d={1,4,4,9,12};if(firstAtLeast(d,4)!=1||firstAtLeast(d,8)!=3)return 6;
 if(9/4+9%4!=3)return 7;
 int s=0;for(int i=0;i<5;++i){if(i%2==0)s+=i;else s-=1;}if(s!=4)return 8;
 return 0;
}`;
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'apcs-free7-'));
const source = path.join(tmp, 'qa.cpp'); const binary = path.join(tmp, 'qa');
fs.writeFileSync(source, cpp);
const compiler = spawnSync('g++', ['-std=c++17','-Wall','-Wextra','-pedantic',source,'-o',binary], { encoding:'utf8' });
if (compiler.status !== 0) errors.push(`C++17 compile QA failed: ${compiler.stderr || compiler.stdout}`);
else {
  const run = spawnSync(binary, [], { encoding:'utf8', timeout:5000 });
  if (run.status !== 0) errors.push(`C++ answer QA failed with exit ${run.status}`);
}
fs.rmSync(tmp, { recursive:true, force:true });

if (errors.length) { console.error(errors.join('\n')); process.exit(1); }
console.log('FREE-7DAY content: VALID');
console.log('FREE-7DAY C++17 QA: PASS');
