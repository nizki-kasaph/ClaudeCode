#!/usr/bin/env python3
"""Asana の [AI自動起票] 未完了タスク全件の総当たりで「実質同じ依頼か」を JEV Noul に掛け、重複の組（グループ）を出す（2026-09-22）。
入力 vm_samples/triage_tasks.json（pull_triage_tasks.py）。出力 vm_samples/asana_dupe_groups.json。閉じる操作はしない。"""
import json, os, sys, time, itertools, collections
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "OpenClaw_Pinay", "scripts"))
from jev_noul import ask_many
HERE = os.path.dirname(__file__)
CTX = ("家事代行会社の社内 LINE 窓口に社員が送った要望・不具合報告を AI が Asana に起票したタスクの一覧。"
       "`pairs` の各要素は 2 件のタスク（title と description）。同じ依頼が二重に起票されたものを見つけたい。")
CRIT = {"true": "同じ画面・機能・不具合について同じことを求めている（言い回しや粒度が違うだけで、1 件にまとめるべき）",
        "false": "別の機能・別の画面・別の目的の依頼で、分けて管理すべき"}
THRESH = float(os.environ.get("DUPE_THRESHOLD", "0.9"))
def main():
    d = json.load(open(os.path.join(HERE, "..", "vm_samples", "triage_tasks.json")))
    d = [t for t in d if not t.get("completed")]
    d.sort(key=lambda t: t.get("created_at") or "")
    pairs = list(itertools.combinations(range(len(d)), 2))
    print(f"タスク {len(d)} 件 → 組 {len(pairs)}")
    prob = {}
    t0 = time.time()
    for s in range(0, len(pairs), 20):
        chunk = pairs[s:s+20]
        st = {f"p{k}": {"a": {"title": d[i]["title"], "description": (d[i].get("description") or "")[:300]},
                        "b": {"title": d[j]["title"], "description": (d[j].get("description") or "")[:300]}} for k, (i, j) in enumerate(chunk)}
        qs = {pid: {"type": "noul", "instructions": f"`pairs.{pid}.a` と `pairs.{pid}.b` は実質同じ依頼（1 件にまとめるべき）ですか？", "criteria": CRIT} for pid in st}
        ans = ask_many(CTX, qs, state={"pairs": st}, timeout=30.0)
        if not ans: print("  batch failed", s); continue
        for k, (i, j) in enumerate(chunk):
            try: prob[(i, j)] = float(ans[f"p{k}"]["noul"])
            except Exception: pass
    print(f"JEV {time.time()-t0:.1f} 秒、判定 {len(prob)}/{len(pairs)}")
    dist = collections.Counter("≥0.9" if p >= 0.9 else "0.5-0.9" if p >= 0.5 else "0.2-0.5" if p >= 0.2 else "<0.2" for p in prob.values())
    print("分布:", dict(dist))
    # 連結成分でグループ化（≥THRESH）
    parent = list(range(len(d)))
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for (i, j), p in prob.items():
        if p >= THRESH: parent[find(i)] = find(j)
    groups = collections.defaultdict(list)
    for i in range(len(d)): groups[find(i)].append(i)
    gs = [g for g in groups.values() if len(g) > 1]
    gs.sort(key=lambda g: -len(g))
    print(f"\n重複グループ（≥{THRESH}）: {len(gs)} 組、対象タスク {sum(len(g) for g in gs)} 件、閉じられる候補 {sum(len(g)-1 for g in gs)} 件")
    for g in gs:
        print(f"--- {len(g)} 件")
        for i in g: print(f"   {d[i]['created_at'][:10]} {d[i]['gid']} {d[i]['title'][:60]}")
    gray = [(p, i, j) for (i, j), p in prob.items() if 0.5 <= p < THRESH]
    print(f"\n要確認帯 0.5〜{THRESH}: {len(gray)} 組")
    for p, i, j in sorted(gray, reverse=True)[:10]: print(f"   {p:.2f} {d[i]['title'][:40]} ⇔ {d[j]['title'][:40]}")
    json.dump({"threshold": THRESH, "groups": [[{"gid": d[i]["gid"], "created_at": d[i]["created_at"], "title": d[i]["title"]} for i in g] for g in gs],
               "gray": [{"p": p, "a": d[i]["gid"], "b": d[j]["gid"]} for p, i, j in gray]},
              open(os.path.join(HERE, "..", "vm_samples", "asana_dupe_groups.json"), "w"), ensure_ascii=False, indent=1)
if __name__ == "__main__": main()
