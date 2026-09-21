#!/usr/bin/env python3
"""error-triage の原因分類で other（分類不能）に落ちた記録を JEV Choice で分類できるか（2026-09-22 実測）。
データ: vm_samples/jev_probe_20260922/.openclaw/workspace/logs/error_triage.jsonl（VM の 30 日分）。
"""
import json, re, sys, os, time, collections
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "OpenClaw_Pinay", "scripts"))
from jev_noul import ask_many
SRC = os.path.join(os.path.dirname(__file__), "..", "vm_samples", "jev_probe_20260922", ".openclaw/workspace/logs/error_triage.jsonl")
CATS = {
    "permission": "権限が無い（403・permission denied・forbidden・アクセス拒否・許可されていないパス）",
    "auth": "認証の失効・不正（401・トークン期限切れ・invalid_grant・OAuth の再認証が要る）",
    "unsupported": "その経路・そのツールでは扱えない（対応していない形式・アプリ認証では不可・未対応モデル）",
    "not_found": "対象が無い（404・ファイル／コマンド／モジュール／セッション／予定が見つからない）",
    "rate_limit": "呼び出し過多・ボット判定・クォータ超過（429・rate limit・bot detection）",
    "timeout": "時間切れ",
    "network": "接続失敗（DNS・接続拒否・リセット・SSL）",
    "script_error": "プログラムの例外・構文エラー（Traceback・TypeError など）",
    "disk": "ディスク容量",
    "guard_block": "Mugi の動作規則のガード／ゲートが意図的に止めた（【〜ゲート】【〜ガード】の停止文）",
    "input_error": "呼び出し方の誤り（引数不正・usage 表示・NEED_/FAILED_ の聞き返し・パラメータ検証失敗）",
    "harmless": "実害の無い中断・通知（利用者の次メッセージで打ち切り・終了要求・警告行だけ）",
    "other": "上のどれにも当たらない",
}
CTX = ("社内 AI アシスタント Mugi のツール呼び出しが失敗したときの本文（先頭部分）の一覧。`rows` の各要素が 1 件。"
       "原因の分類は運用担当が『権限・認証は要システム連絡、呼び出し方の誤りは手順の直し、ガード停止は設計どおり』と振り分けるために使う。")
def q(rid):
    return {"type": "choice", "instructions": f"`rows.{rid}` の失敗の原因分類はどれですか？", "criteria": CATS}
def norm(s): return re.sub(r"\d+", "#", (s or "")[:160])
def main():
    since = time.time()*1000 - 30*86400*1000
    rows = [json.loads(l) for l in open(SRC) if l.strip()]
    other = [r for r in rows if r.get("cat") == "other" and (r.get("ts_ms") or 0) >= since]
    groups = collections.OrderedDict()
    for r in other: groups.setdefault(norm(r.get("sig")), []).append(r)
    keys = list(groups)
    print(f"other 30 日: {len(other)} 件 → 署名の重複除去 {len(keys)} 種")
    t0 = time.time(); res = {}
    for s in range(0, len(keys), 20):
        chunk = keys[s:s+20]
        rows_ = {f"r{k+1}": {"tool": groups[key][0].get("tool"), "text": groups[key][0].get("sig")} for k, key in enumerate(chunk)}
        ans = ask_many(CTX, {rid: q(rid) for rid in rows_}, state={"rows": rows_}, timeout=30.0)
        if not ans: print("  batch failed", s); continue
        for k, key in enumerate(chunk):
            a = ans.get(f"r{k+1}") or {}
            res[key] = (a.get("choice"), a.get("confidence"))
    print(f"JEV Choice {time.time()-t0:.1f} 秒")
    bycat = collections.Counter(); byn = collections.Counter()
    for key in keys:
        ch, cf = res.get(key, (None, None)); n = len(groups[key])
        bycat[ch] += 1; byn[ch] += n
    print("\n分類 → 署名の種類数 / 件数")
    for ch, n in byn.most_common(): print(f"  {str(ch):13s} {bycat[ch]:3d} 種 {n:4d} 件")
    print("\n各署名（件数・分類・確信度・本文）")
    for key in sorted(keys, key=lambda k: -len(groups[k])):
        ch, cf = res.get(key, (None, None))
        print(f"  ×{len(groups[key]):3d} {str(ch):13s} {cf if cf is None else round(cf,2)!s:5s} {groups[key][0].get('tool') or '':14s} {(groups[key][0].get('sig') or '')[:95]!r}")
    json.dump({k: {"n": len(groups[k]), "choice": res.get(k), "tool": groups[k][0].get("tool"), "sig": groups[k][0].get("sig")} for k in keys},
              open(os.path.join(os.path.dirname(SRC), "../../../error_triage_choice_results.json"), "w"), ensure_ascii=False, indent=1)
if __name__ == "__main__":
    main()
