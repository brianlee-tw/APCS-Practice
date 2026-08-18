#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,datetime as dt,re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"; DOCS=ROOT/"docs"; NOTES=ROOT/"notes"
PROGRESS=DATA/"progress.csv"; REVIEWS=DATA/"reviews.csv"
INDEX=DOCS/"PROBLEM_INDEX.md"; QUEUE=DOCS/"REVIEW_QUEUE.md"
SUFFIXES={".cpp",".py"}
EXCLUDE={".git",".github",".vscode","tools","docs","data","notes","build","Build","__pycache__"}
START="<!-- APCS_DASHBOARD_START -->"; END="<!-- APCS_DASHBOARD_END -->"
ID_RE=re.compile(r"([a-z]\d+)",re.I)
META_RE=re.compile(r"^(?://|#)\s*APCS\s+([^:]+):\s*(.*?)\s*$",re.I)
DATE_FORMATS=("%Y-%m-%d","%y-%m-%d")
VALID={"","AC","WA","TLE","MLE","RE","CE"}

@dataclass
class Sol:
    path:Path; pid:str; meta:dict[str,str]
    @property
    def title(self): return self.meta.get("title") or self.path.stem
    @property
    def tags(self): return [x.strip() for x in self.meta.get("tag","").split(",") if x.strip()]
    @property
    def complexity(self): return self.meta.get("complexity") or "—"
    @property
    def difficulty(self):
        try:return max(1,min(5,int(self.meta.get("difficulty","1"))))
        except:return 1
    @property
    def note(self): return self.meta.get("note","")
    @property
    def legacy_date(self): return parse_date(self.meta.get("date",""))

@dataclass
class State:
    verdict:str=""; solved:dt.date|None=None; reviewed:dt.date|None=None; recall:int|None=None

def norm(v:str|None)->str:
    m=ID_RE.search((v or "").lower()); return m.group(1) if m else ""

def parse_date(v:str|None):
    s=(v or "").strip()
    for f in DATE_FORMATS:
        try:return dt.datetime.strptime(s,f).date()
        except ValueError:pass
    return None

def date_s(v): return v.isoformat() if v else ""

def ensure():
    DATA.mkdir(exist_ok=True); DOCS.mkdir(exist_ok=True); NOTES.mkdir(exist_ok=True)
    if not PROGRESS.exists(): PROGRESS.write_text("problem_id,verdict,solved,reviewed,recall\n",encoding="utf-8")
    if not REVIEWS.exists(): REVIEWS.write_text("problem_id,date,score,minutes,result,note\n",encoding="utf-8")

def files():
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in SUFFIXES: continue
        rel=p.relative_to(ROOT)
        if any(x in EXCLUDE or x==".cph" for x in rel.parts[:-1]): continue
        if "tempCodeRunner" in p.name: continue
        yield p

def parse_solution(p:Path):
    text="\n".join(p.read_text(encoding="utf-8",errors="ignore").splitlines()[:24])
    meta={}
    for line in text.splitlines():
        m=META_RE.match(line)
        if m: meta[m.group(1).strip().lower()]=m.group(2).strip()
    return Sol(p,norm(p.stem),meta)

def load_progress():
    ensure(); out={}
    with PROGRESS.open(newline="",encoding="utf-8") as f:
        for r in csv.DictReader(f):
            pid=norm(r.get("problem_id"))
            if not pid: continue
            rec=None
            try: rec=int(r["recall"]) if (r.get("recall") or "").strip() else None
            except: pass
            out[pid]=State((r.get("verdict") or "").upper(),parse_date(r.get("solved")),parse_date(r.get("reviewed")),rec)
    return out

def load_reviews():
    ensure(); out=defaultdict(list)
    with REVIEWS.open(newline="",encoding="utf-8") as f:
        for r in csv.DictReader(f):
            pid=norm(r.get("problem_id")); d=parse_date(r.get("date"))
            if not pid or not d: continue
            try: score=int(r.get("score",""))
            except: continue
            out[pid].append((d,score,(r.get("result") or "").upper()))
    for v in out.values():v.sort()
    return out

def domain(sol:Sol):
    t=" ".join(sol.tags+[sol.title,sol.path.stem]).lower()
    rules=[
      ("Graph",["graph","bfs","dfs","dijkstra","topological","mst","union find","dsu"]),
      ("DP / Recursion",["dynamic programming"," dp ","recursion","backtracking","memo"]),
      ("Prefix / Greedy",["prefix","greedy","difference array","sliding window"]),
      ("Search / Sort",["binary search","sorting","sort","two pointers"]),
      ("Data Structures",["stack","queue","deque","heap","priority queue","set","map","hash","tree"]),
      ("Math",["math","prime","factor","gcd","lcm","mod","number theory","geometry"]),
      ("String",["string","char"]),
      ("Arrays / Simulation",["array","vector","matrix","simulation"]),
    ]
    for name,keys in rules:
        if any(k in t for k in keys):return name
    return "Fundamentals / Simulation"

def next_due(state:State,revs):
    if state.verdict!="AC":return None
    anchor=state.reviewed or state.solved
    if not anchor:return None
    score=state.recall
    if score is None:return anchor
    if score<=0:days=1
    elif score==1:days=3
    elif score==2:days=7
    else:
        streak=0
        for _,s,res in reversed(revs):
            if s==3 and (not res or res=="AC"):streak+=1
            else:break
        days=90 if streak>=3 else 60 if streak>=2 else 30
    return anchor+dt.timedelta(days=days)

def build():
    progress=load_progress(); reviews=load_reviews()
    by=defaultdict(list); warnings=[]
    for p in files():
        s=parse_solution(p)
        if not s.pid:
            warnings.append(f"{p.relative_to(ROOT)}: filename has no problem id"); continue
        title_id=norm(s.meta.get("title"))
        if title_id and title_id!=s.pid:
            warnings.append(f"{p.relative_to(ROOT)}: filename id={s.pid}, title id={title_id}")
        by[s.pid].append(s)
    rows=[]
    for pid,ss in sorted(by.items()):
        primary=sorted(ss,key=lambda x:(0 if x.path.suffix==".cpp" else 1,str(x.path)))[0]
        st=progress.get(pid,State())
        legacy_done=any(x.note for x in ss)
        if not st.solved and legacy_done:
            dates=[x.legacy_date for x in ss if x.legacy_date]
            if dates: st.solved=min(dates)
        due=next_due(st,reviews.get(pid,[]))
        rows.append((pid,ss,primary,st,legacy_done,due,domain(primary)))
    return rows,warnings

def link(path:Path,label=None,from_docs=False):
    rel=path.relative_to(ROOT).as_posix(); prefix="../" if from_docs else "./"
    return f"[{label or path.name}]({prefix}{rel})"

def status(st,legacy):
    if st.verdict=="AC":return "✅ AC"
    if st.verdict:return "❌ "+st.verdict
    if legacy:return "📚 Legacy"
    return "📝 Untracked"

def render_dashboard(rows):
    today=dt.date.today(); ac=sum(r[3].verdict=="AC" for r in rows); legacy=sum(r[4] and r[3].verdict!="AC" for r in rows)
    due=sum(bool(r[5] and r[5]<=today) for r in rows); dom=defaultdict(lambda:[0,0,0])
    for r in rows:
        d=dom[r[6]]; d[0]+=1; d[1]+=int(r[3].verdict=="AC" or r[4]); d[2]+=int(bool(r[5] and r[5]<=today))
    lines=["## APCS Training Dashboard","", "| 指標 | 數量 |","| :--- | ---: |",
      f"| 索引題目 | **{len(rows)}** |",f"| 明確標記 AC | **{ac}** |",f"| 舊制完成（有筆記、尚未確認 AC） | **{legacy}** |",f"| 今日到期複習 | **{due}** |","",
      "> `📚 Legacy` 代表舊制資料；v2 不再把 Notion 連結等同於 AC。","","### 能力分布","","| 領域 | 題數 | AC / 舊制完成 | 到期 |","| :--- | ---: | ---: | ---: |"]
    for k,v in sorted(dom.items(),key=lambda x:(-x[1][0],x[0])): lines.append(f"| {k} | {v[0]} | {v[1]} | {v[2]} |")
    lines+=["","### 今日複習優先序","","| ID | 題目 | 領域 | Recall | 到期日 |","| :--- | :--- | :--- | ---: | :---: |"]
    due_rows=[r for r in rows if r[5] and r[5]<=today]
    if due_rows:
        for r in sorted(due_rows,key=lambda x:(x[5],x[0]))[:12]:
            lines.append(f"| `{r[0]}` | {r[2].title} | {r[6]} | {r[3].recall if r[3].recall is not None else '—'} | {r[5]} |")
    else: lines.append("| — | 目前沒有到期題目 | — | — | — |")
    lines+=["","完整題庫見 [Problem Index](./docs/PROBLEM_INDEX.md)，複習佇列見 [Review Queue](./docs/REVIEW_QUEUE.md)。"]
    return "\n".join(lines)

def render_index(rows):
    lines=["# Problem Index","","> 自動產生；請勿手動編輯。","","| ID | 題目 | 領域 | 程式 | 複雜度 | 難度 | 狀態 | Recall | 筆記 |","| :--- | :--- | :--- | :--- | :--- | :---: | :---: | ---: | :--- |"]
    for pid,ss,p,st,legacy,due,dom in rows:
        progs="<br>".join(link(x.path,"C++" if x.path.suffix==".cpp" else "Py",True) for x in sorted(ss,key=lambda x:x.path.suffix))
        local=NOTES/f"{pid}.md"; note=link(local,"Local",True) if local.exists() else next((f"[Notion]({x.note})" for x in ss if x.note),"—")
        lines.append(f"| `{pid}` | {p.title} | {dom} | {progs} | `{p.complexity}` | {'★'*p.difficulty} | {status(st,legacy)} | {st.recall if st.recall is not None else '—'} | {note} |")
    return "\n".join(lines)+"\n"

def render_queue(rows):
    today=dt.date.today(); q=[r for r in rows if r[3].verdict=="AC" and r[5]]
    lines=["# Review Queue","","> 自動產生；依 adaptive review 排序。","","| 到期日 | ID | 題目 | 領域 | Recall | 狀態 |","| :---: | :--- | :--- | :--- | ---: | :---: |"]
    if not q: lines.append("| — | — | 尚無明確 AC / review 資料 | — | — | — |")
    for r in sorted(q,key=lambda x:(x[5],x[0])):
        mark="🔴 到期" if r[5]<=today else "🟢 排程"; lines.append(f"| {r[5]} | `{r[0]}` | {r[2].title} | {r[6]} | {r[3].recall if r[3].recall is not None else '—'} | {mark} |")
    return "\n".join(lines)+"\n"

def replace_between(text,start,end,body):
    if start in text and end in text:
        a,b=text.split(start,1); _,c=b.split(end,1); return a+start+"\n"+body+"\n"+end+c
    return text.rstrip()+f"\n\n{start}\n{body}\n{end}\n"

def sync():
    ensure(); rows,w=build(); readme=ROOT/"README.md"; text=readme.read_text(encoding="utf-8") if readme.exists() else "# APCS-Practice\n"
    readme.write_text(replace_between(text,START,END,render_dashboard(rows)),encoding="utf-8"); INDEX.write_text(render_index(rows),encoding="utf-8"); QUEUE.write_text(render_queue(rows),encoding="utf-8")
    print(f"Synced {len(rows)} problems.")
    if w: print(f"{len(w)} warning(s); run validate for details.")
    return 0

def validate(strict=False):
    ensure(); rows,w=build(); errors=[]
    for _,ss,_,_,_,_,_ in rows:
        for s in ss:
            rel=s.path.relative_to(ROOT)
            if not s.meta.get("title"): w.append(f"{rel}: missing APCS Title")
            if not s.tags:w.append(f"{rel}: missing APCS Tag")
            if s.complexity=="—":w.append(f"{rel}: missing APCS Complexity")
    for pid,st in load_progress().items():
        if st.verdict not in VALID:errors.append(f"progress: invalid verdict {st.verdict} for {pid}")
        if st.recall is not None and not 0<=st.recall<=3:errors.append(f"progress: recall must be 0-3 for {pid}")
    print(f"Problems: {len(rows)} | Errors: {len(errors)} | Warnings: {len(w)}")
    for x in errors:print("ERROR:",x)
    for x in w:print("WARN:",x)
    return 1 if errors or (strict and w) else 0

def save_progress(pid,verdict,score,date):
    rows=[]
    if PROGRESS.exists():
        with PROGRESS.open(newline="",encoding="utf-8") as f:rows=list(csv.DictReader(f))
    found=False
    for r in rows:
        if norm(r.get("problem_id"))==pid:
            found=True; old_solved=r.get("solved",""); r.update(problem_id=pid,verdict=verdict,solved=old_solved or (date_s(date) if verdict=="AC" else ""),reviewed=date_s(date),recall=str(score))
    if not found:rows.append({"problem_id":pid,"verdict":verdict,"solved":date_s(date) if verdict=="AC" else "","reviewed":date_s(date),"recall":str(score)})
    with PROGRESS.open("w",newline="",encoding="utf-8") as f:
        wr=csv.DictWriter(f,fieldnames=["problem_id","verdict","solved","reviewed","recall"]);wr.writeheader();wr.writerows(rows)

def record(pid,score,result="AC",minutes=None,note=""):
    ensure(); rows,_=build()
    if pid not in {r[0] for r in rows}: raise SystemExit(f"Unknown problem id: {pid}")
    if not 0<=score<=3: raise SystemExit("Recall score must be 0..3")
    today=dt.date.today(); save_progress(pid,result,score,today)
    with REVIEWS.open("a",newline="",encoding="utf-8") as f: csv.writer(f).writerow([pid,date_s(today),score,minutes or "",result,note])
    sync(); print(f"Recorded {pid}: {result}, recall={score}/3"); return 0

def today_cmd():
    rows,_=build(); today=dt.date.today(); q=[r for r in rows if r[5] and r[5]<=today]
    if not q: print("No review is due today."); return 0
    for r in sorted(q,key=lambda x:(x[5],x[0])): print(f"{r[5]}  {r[0]}  recall={r[3].recall}  {r[2].title}")
    return 0

def note_cmd(pid):
    rows,_=build(); table={r[0]:r for r in rows}
    if pid not in table: raise SystemExit(f"Unknown problem id: {pid}")
    path=NOTES/f"{pid}.md"
    if path.exists():print(path.relative_to(ROOT));return 0
    title=table[pid][2].title; path.write_text(f"# {pid} — {title}\n\n## 一句話解法\n\n-\n\n## 我卡住的地方\n\n-\n\n## 關鍵觀念 / 模板\n\n-\n\n## 下次重解注意\n\n-\n",encoding="utf-8"); print(path.relative_to(ROOT));return 0

def main(argv=None):
    ap=argparse.ArgumentParser(description="APCS-Practice v2 learning workflow"); sp=ap.add_subparsers(dest="cmd",required=True)
    sp.add_parser("sync"); v=sp.add_parser("validate");v.add_argument("--strict",action="store_true"); sp.add_parser("today")
    for name in ("finish","review"):
        p=sp.add_parser(name);p.add_argument("problem_id");p.add_argument("score",type=int);p.add_argument("--result",default="AC",choices=sorted(x for x in VALID if x));p.add_argument("--minutes",type=int);p.add_argument("--note",default="")
    n=sp.add_parser("note");n.add_argument("problem_id"); a=ap.parse_args(argv)
    if a.cmd=="sync":return sync()
    if a.cmd=="validate":return validate(a.strict)
    if a.cmd=="today":return today_cmd()
    if a.cmd in ("finish","review"):return record(norm(a.problem_id),a.score,a.result,a.minutes,a.note)
    if a.cmd=="note":return note_cmd(norm(a.problem_id))
    return 2

if __name__=="__main__":raise SystemExit(main())
