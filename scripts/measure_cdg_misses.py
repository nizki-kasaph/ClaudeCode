#!/usr/bin/env python3
"""code-delegation-gate の見逃し実測（2026-09-22）。
VM の transcript_events 30 日分（vm_samples/jev_probe_20260922/jev_probe_transcripts.json）から
本体セッション（subagent/dashboard でない）の exec / write / edit / apply_patch 呼び出しを取り、
プラグインの正規表現（isCodeAuthoringCommand / CODE_EXT_RE の Python 移植）で当たる・当たらないを分け、
結果本文にゲートの blockReason が入ったかで「実際に止まった」を確認する。
  python3 scripts/measure_cdg_misses.py                # 語彙の当たり外れの一覧（JEV なし）
  python3 scripts/measure_cdg_misses.py --jev          # 語彙に当たらなかった exec を JEV Noul に掛ける（TYPESAFE_API_KEY）
"""
import json, re, sys, os, time, collections
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "OpenClaw_Pinay", "scripts"))
SRC = os.path.join(os.path.dirname(__file__), "..", "vm_samples", "jev_probe_20260922", "jev_probe_transcripts.json")
OUT = os.path.join(os.path.dirname(__file__), "..", "vm_samples", "jev_probe_20260922", "cdg_inventory.json")

CODE_EXT_RE = re.compile(r"\.(py|pyw|js|mjs|cjs|ts|tsx|jsx|sh|bash|zsh|gs|html?|css|scss|sql|rb|go|java|kt|php|ps1|pl|rs|c|cc|cpp|h|hpp|swift|lua|r|ipynb)$", re.I)
INLINE_EXEC_RE = re.compile(r"""(?:^|[\s;&|(`'"])(?:python[23]?(?:\.\d+)?|node|nodejs|bun|ruby|perl|php)(?:\s+-[A-Za-z][A-Za-z0-9-]*(?:=\S*)?)*\s+(?:-c|-e|--eval|-r)(?:\s|$)|(?:^|[\s;&|(`'"])deno\s+eval\b""")
HEREDOC_RE = re.compile(r"""<<-?\s*['"]?[A-Za-z_][A-Za-z0-9_]*['"]?""")
FILEGEN_RE = re.compile(r"\b(cat|tee|printf|echo)\b[^|;&]*>\s*\S*\.(py|js|mjs|cjs|ts|sh|bash|gs|html?|css|sql|rb|go|php)\b", re.I)
SCAFFOLD_RE = re.compile(r"\bnpm\s+init\b|\bnpx\s+create-")

def is_code_authoring(cmd: str) -> str:
    if INLINE_EXEC_RE.search(cmd): return "inline"
    if HEREDOC_RE.search(cmd): return "heredoc"
    if FILEGEN_RE.search(cmd): return "filegen"
    if SCAFFOLD_RE.search(cmd): return "scaffold"
    return ""

BLOCK_MARK = re.compile(r"sessions_spawn|委譲")

def main():
    data = json.load(open(SRC))
    rows = []
    for s in data["sessions"]:
        sid = s["session"]
        if ":subagent:" in sid or ":dashboard:" in sid: continue
        results = {}
        for ev in s["events"]:
            for it in ev["items"]:
                if it["t"] == "result" and it.get("id"): results[it["id"]] = it["v"]
        last_user = ""
        for ev in s["events"]:
            for it in ev["items"]:
                if it["t"] == "text": last_user = it["v"]
                if it["t"] != "tool": continue
                name, a = it["name"], it["args"]
                if name == "sessions_spawn": continue
                r = results.get(it.get("id"), "")
                blocked = bool(BLOCK_MARK.search(r)) and ("block" in r.lower() or "【" in r)
                if name == "exec":
                    cmd = a.get("command", "")
                    hit = is_code_authoring(cmd)
                    rows.append({"agent": s["agent"], "session": sid[-40:], "ts": ev["ts"], "tool": "exec", "hit": hit, "blocked": blocked,
                                 "text": cmd[:300], "user": last_user[:200]})
                else:
                    p = a.get("path") or a.get("file_path") or a.get("filePath") or ""
                    hit = "codeext" if CODE_EXT_RE.search(p) else ""
                    rows.append({"agent": s["agent"], "session": sid[-40:], "ts": ev["ts"], "tool": name, "hit": hit, "blocked": blocked,
                                 "text": (p + " | " + str(a.get("content", ""))[:200])[:300], "user": last_user[:200]})
    json.dump(rows, open(OUT, "w"), ensure_ascii=False, indent=1)
    c = collections.Counter((r["tool"], bool(r["hit"]), r["blocked"]) for r in rows)
    print("tool, regex_hit, blocked -> n")
    for k, n in sorted(c.items()): print(" ", k, n)
    print("agents:", collections.Counter(r["agent"] for r in rows))
    miss = [r for r in rows if r["tool"] == "exec" and not r["hit"]]
    print(f"\n語彙に当たらなかった exec: {len(miss)} 件。先頭語の分布:")
    heads = collections.Counter(re.split(r"[\s|;&]+", r["text"].strip())[0][:20] for r in miss)
    for h, n in heads.most_common(25): print(f"  {n:4d} {h}")
    hit_nb = [r for r in rows if r["hit"] and not r["blocked"]]
    print(f"\n語彙に当たったのに blocked の痕跡が無い: {len(hit_nb)} 件（結果本文の取り方の限界か、要目視）")
    for r in hit_nb[:8]: print("   ", r["agent"], r["hit"], r["text"][:120].replace("\n", "⏎"))

if __name__ == "__main__" and "--jev" not in sys.argv:
    main()


# ===== --jev: 語彙に当たらなかった exec と、利用者の依頼文を JEV Noul に掛ける（2026-09-22） =====
CMD_CTX = ("Mugi（社内 AI アシスタント）が実行しようとしたシェルコマンドの一覧。`rows` の各要素が 1 コマンド。"
           "「コードを組む動作」= 新しいプログラム・スクリプトのソースを書く／生成する／インライン実行する動作。"
           "既存スクリプトの実行、ファイル一覧・検索・閲覧、パッケージ導入、cron の確認などは「組む動作」ではない。")
def cmd_q(rid):
    return {"type": "noul", "instructions": f"`rows.{rid}` のコマンドは「コードを組む動作」ですか？",
            "criteria": {"true": "新しいプログラム・スクリプトのソースコードを書く、生成する、またはコードをその場で与えて実行している",
                         "false": "既存のスクリプトやコマンドを実行・閲覧・確認しているだけで、新しいコードは書いていない"}}
REQ_CTX = ("家事代行会社の社内 AI アシスタント Mugi への、社員からの依頼文の一覧。`rows` の各要素が 1 通。"
           "「コード生成の依頼」= プログラム・スクリプト・関数・自動化のコードを新しく書いてほしいという依頼。"
           "データの抽出・集計・シート出力・予定の登録・文章作成・質問などは、裏でコードが要るとしても「コード生成の依頼」ではない。")
def req_q(rid):
    return {"type": "noul", "instructions": f"`rows.{rid}` はコード生成の依頼ですか？",
            "criteria": {"true": "プログラム・スクリプト・コードそのものを書く／作ることを求めている",
                         "false": "コードを求めていない（結果・作業・回答を求めている）"}}

def jev_batch(ctx, qfn, texts, batch=20):
    from jev_noul import ask_many
    out = [None] * len(texts)
    for s in range(0, len(texts), batch):
        rows = {f"r{k+1}": texts[s+k] for k in range(min(batch, len(texts) - s))}
        ans = ask_many(ctx, {rid: qfn(rid) for rid in rows}, state={"rows": rows}, timeout=30.0)
        if not ans: print("  batch failed", s); continue
        for k in range(len(rows)):
            try: out[s+k] = float(ans[f"r{k+1}"]["noul"])
            except Exception: pass
    return out

def strip_cd(c): return re.sub(r"^\s*cd\s+\S+\s*(&&|;)\s*", "", c.strip())

def main_jev():
    rows = json.load(open(OUT))
    data = json.load(open(SRC))
    t0 = time.time()
    # A. 語彙に当たらなかった exec（重複除去）
    un = collections.OrderedDict()
    for r in rows:
        if r["tool"] == "exec" and not r["hit"]:
            k = strip_cd(r["text"])[:300]
            if k: un.setdefault(k, 0); un[k] += 1
    cmds = list(un)
    pa = jev_batch(CMD_CTX, cmd_q, cmds)
    print(f"=== A. 語彙に当たらなかった exec: {len(rows_ex := [r for r in rows if r['tool']=='exec' and not r['hit']])} 件 → 重複除去 {len(cmds)} 件、JEV {time.time()-t0:.1f} 秒")
    hi = [(p, c, un[c]) for p, c in zip(pa, cmds) if p is not None and p >= 0.5]
    print(f"  Noul ≥0.5（見逃し候補）: {len(hi)} 種 / 呼び出し {sum(n for _,_,n in hi)} 回")
    for p, c, n in sorted(hi, reverse=True)[:30]: print(f"   {p:.2f} ×{n:3d} {c[:130]!r}")
    dist = collections.Counter("≥0.5" if p >= 0.5 else "0.2-0.5" if p >= 0.2 else "<0.2" for p in pa if p is not None)
    print("  分布:", dict(dist), " 失敗:", sum(1 for p in pa if p is None))
    # B. 利用者の依頼文（本体セッション）
    t1 = time.time()
    reqs = collections.OrderedDict()  # text -> [(agent, session, ts, followed_by_spawn_or_block)]
    for s in data["sessions"]:
        sid = s["session"]
        if ":subagent:" in sid or ":dashboard:" in sid: continue
        evs = s["events"]
        for i, ev in enumerate(evs):
            for it in ev["items"]:
                if it["t"] != "text": continue
                t = it["v"].strip()
                if len(t) < 6 or t.startswith(("<<<BEGIN_OPENCLAW", "[Subagent", "[Cron", "[Heartbeat", "System:", "[System")): continue
                # 次の利用者発話までに sessions_spawn か 委譲ゲート block があったか
                follow = False
                for ev2 in evs[i+1:]:
                    stop = False
                    for it2 in ev2["items"]:
                        if it2["t"] == "text": stop = True; break
                        if it2["t"] == "tool" and it2["name"] == "sessions_spawn": follow = True
                        if it2["t"] == "result" and "委譲ゲート" in it2["v"]: follow = True
                    if stop: break
                reqs.setdefault(t[:300], []).append((s["agent"], sid[-20:], ev["ts"], follow))
    texts = list(reqs)
    pb = jev_batch(REQ_CTX, req_q, texts)
    print(f"\n=== B. 利用者の依頼文: {sum(len(v) for v in reqs.values())} 通 → 重複除去 {len(texts)} 通、JEV {time.time()-t1:.1f} 秒")
    hib = [(p, t) for p, t in zip(pb, texts) if p is not None and p >= 0.5]
    print(f"  「コード生成の依頼」≥0.5: {len(hib)} 通")
    for p, t in sorted(hib, reverse=True)[:25]:
        occ = reqs[t]
        f = sum(1 for o in occ if o[3])
        print(f"   {p:.2f} {occ[0][0]:12s} 委譲/停止あり {f}/{len(occ)} | {t[:110]!r}")
    dist = collections.Counter("≥0.5" if p >= 0.5 else "0.2-0.5" if p >= 0.2 else "<0.2" for p in pb if p is not None)
    print("  分布:", dict(dist), " 失敗:", sum(1 for p in pb if p is None))
    json.dump({"cmds": [(p, c, un[c]) for p, c in zip(pa, cmds)], "reqs": [(p, t, reqs[t]) for p, t in zip(pb, texts)]},
              open(OUT.replace("cdg_inventory", "cdg_jev_results"), "w"), ensure_ascii=False, indent=1)

if __name__ == "__main__" and "--jev" in sys.argv:
    main_jev()
