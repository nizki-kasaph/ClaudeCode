"""line-asana-triage の JEV 候補の実測（2026-09-21）。
  1. 同じ元テキストから複数タスクが作られた構造（件数・作成時刻の幅）
  2. 区分（要望／不具合）を JEV Choice で判定し Gemini の区分と比較
  3. 同じ元テキスト内のタスク同士が「同じ依頼」かを JEV Noul で判定（重複検知）
使い方: python3 scripts/measure_triage_category_dedup.py vm_samples   （triage_tasks.json は scripts/pull_triage_tasks.py で取得）
キーは JEV-UsageGuide/.env の TYPESAFE_API_KEY。OpenClaw_Pinay/scripts/jev_noul.py の ask_many を使う。"""
import json, sys, os, time, itertools
from collections import defaultdict, Counter
sys.path.insert(0, "/Users/NIZ-ki/Documents/Claude/OpenClaw_Pinay/scripts")
from dotenv import load_dotenv
load_dotenv("/Users/NIZ-ki/Documents/Claude/JEV-UsageGuide/.env")
from jev_noul import ask_many
S = sys.argv[1]
d = json.load(open(S + "/triage_tasks.json")); d.sort(key=lambda o: o["created_at"])
for i, o in enumerate(d): o["idx"] = i

# 1. 重複の構造: 同じ元テキストから何件・何回の実行で作られたか
groups = defaultdict(list)
for o in d: groups[o["source"]].append(o)
multi = {k: v for k, v in groups.items() if len(v) > 1}
print("=== 1. 同じ元テキストから複数タスク:", len(multi), "組 /", sum(len(v) for v in multi.values()), "件")
for k, v in multi.items():
    ts = sorted(o["created_at"] for o in v)
    span = (time.mktime(time.strptime(ts[-1][:19], "%Y-%m-%dT%H:%M:%S")) - time.mktime(time.strptime(ts[0][:19], "%Y-%m-%dT%H:%M:%S")))
    print(f"  idx={[o['idx'] for o in v]} 件数={len(v)} 作成の幅={span:.0f}秒 先頭: {v[0]['title'][:30]}")

# 2. 区分（要望/不具合）を JEV Choice で判定し、Gemini と比較
CTX = ("家事代行会社の社内 IT 窓口。社員が LINE で送ったシステムへの依頼を AI が整理した。`rows.rN` は整理後の 1 件（title と description）。"
       "『不具合』は既存機能が期待どおり動かない・誤った結果を出す・エラーになる報告。『要望』は新機能・改善・確認依頼・質問など、動作不良の報告ではないもの。")
def qcat(rid):
    return {"type": "choice", "instructions": f"`rows.{rid}` の依頼はどちらですか？",
            "criteria": {"不具合": "既存の機能が期待どおりに動かない・誤った結果を出す・エラーが出るという報告（遅い・表示されない・反映されない・数字が合わない も含む）",
                         "要望": "新しい機能・改善・設定変更・確認依頼・質問・検討依頼など、動作不良の報告ではないもの"}}
results = {}
t0 = time.time()
for i in range(0, len(d), 20):
    chunk = d[i:i + 20]
    rows = {f"r{k+1}": {"title": o["title"], "description": o["description"][:400]} for k, o in enumerate(chunk)}
    qs = {rid: qcat(rid) for rid in rows}
    ans = ask_many(CTX, qs, state={"rows": rows}, timeout=20.0)
    if not ans: print("  batch failed", i); continue
    for k, o in enumerate(chunk):
        a = ans.get(f"r{k+1}") or {}
        results[o["idx"]] = (a.get("choice"), a.get("confidence"))
print(f"=== 2. 区分の JEV 判定 ({time.time()-t0:.1f} 秒, {len(results)}/{len(d)} 件)")
agree = sum(1 for o in d if results.get(o["idx"], (None,))[0] == o["category"])
print("  Gemini と一致:", agree, "/", len(results))
print("  不一致（idx Gemini→JEV conf | title）:")
for o in d:
    c, conf = results.get(o["idx"], (None, None))
    if c != o["category"]:
        print(f"   {o['idx']:2d} {o['category']}→{c} {conf} | {o['title'][:45]}")
low = [(o["idx"], results[o["idx"]]) for o in d if o["idx"] in results and (results[o["idx"]][1] or 0) < 0.7]
print("  confidence<0.7:", low)

# 3. 同じ元テキスト内のタスク同士が「同じ依頼」か（Noul）
CTX2 = "家事代行会社の社内 IT 窓口。同じ LINE メッセージから AI が切り出した依頼 `a` と `b`。"
Q2 = {"type": "noul", "instructions": "`a` と `b` は実質同じ依頼（同じ機能・同じ不具合を指し、1 件にまとめるべき）ですか？",
      "criteria": {"true": "同じ画面・機能・不具合について同じことを求めている（言い回しや粒度が違うだけ）",
                   "false": "別の機能・別の画面・別の目的の依頼で、分けて管理すべき"}}
pairs = []
for k, v in multi.items():
    for a, b in itertools.combinations(v, 2): pairs.append((a, b))
print("=== 3. 同じ元テキスト内のペア:", len(pairs))
t0 = time.time(); same = []
for i in range(0, len(pairs), 20):
    chunk = pairs[i:i + 20]
    st = {f"p{k+1}": {"a": {"title": a["title"], "description": a["description"][:300]}, "b": {"title": b["title"], "description": b["description"][:300]}} for k, (a, b) in enumerate(chunk)}
    qs = {pid: {"type": "noul", "instructions": f"`pairs.{pid}.a` と `pairs.{pid}.b` は実質同じ依頼（1 件にまとめるべき）ですか？", "criteria": Q2["criteria"]} for pid in st}
    ans = ask_many(CTX2, qs, state={"pairs": st}, timeout=20.0)
    if not ans: print("  batch failed", i); continue
    for k, (a, b) in enumerate(chunk):
        p = (ans.get(f"p{k+1}") or {}).get("noul")
        same.append((a["idx"], b["idx"], p))
print(f"  ({time.time()-t0:.1f} 秒)")
for a, b, p in same: print(f"   {a:2d}-{b:2d} noul={p} | {d[a]['title'][:28]} / {d[b]['title'][:28]}")
print("  0.6 以上（同じ依頼）:", sum(1 for _, _, p in same if p is not None and p >= 0.6), "/", len(same))
json.dump({"category": {str(k): v for k, v in results.items()}, "same": same}, open(S + "/triage_jev_results.json", "w"), ensure_ascii=False, indent=1)
