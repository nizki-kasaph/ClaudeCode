"""組み込み先 3（pinay_pick の判定 `judge`）: 行ごとの自由記述を「条件に当たるか」で判定する呼び方を実測する。

- まとめ呼び: state に 20 行を入れ、質問を 20 個（r1..r20）付けて 1 回で判定
- 1 行ずつ: 同じ行を 1 行 1 回で判定（精度の比較用）
条件 3 つ × 20 行（true 10 / false 10）。合成データ（個人名なし）。

使い方: python3 scripts/measure_judge_batch.py [--out vm_samples/jev_judge_batch_v1.json] [--no-single]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "client"))
from jev_client import JevClient  # noqa: E402

CONTEXT = (
    "当社は家事代行（ハウスキーピング）の会社。`rows` は社内台帳から抽出した行ごとの自由記述（顧客の特記事項・解約イベントの内容・"
    "スタッフのイベント内容など）。`criterion` は依頼者が指定した絞り込みの条件。"
)


def question_for(rid: str) -> dict:
    return {
        "type": "noul",
        "instructions": f"`rows.{rid}` の記述は、`criterion` の条件に当てはまりますか？",
        "criteria": {
            "true": "記述の内容が条件に該当することを示している（言い回しが違っても、意味として該当する）",
            "false": "条件に該当しない、または条件について何も書かれていない・判断できる記述が無い",
        },
    }


SETS = {
    "moving": {
        "criterion": "引越し（転居）が理由で解約した",
        "rows": [
            ("転居のため解約", True), ("引っ越しに伴い終了希望", True), ("9月末で退去、新居では利用しない", True),
            ("実家に戻ることになったため", True), ("海外赴任で解約", True), ("転勤で大阪へ", True),
            ("住み替えのためサービス終了", True), ("新居が対象エリア外のため", True), ("引越し先が遠方になる", True), ("マンション売却に伴い解約", True),
            ("料金が高いとのこと", False), ("スタッフとの相性が合わず", False), ("体調不良で一時停止→そのまま解約", False),
            ("自分でできるようになったため", False), ("", False), ("引越しはしないが、しばらく休みたいとのこと", False),
            ("他社サービスに切替", False), ("家族が同居することになり不要に", False), ("子どもが独立して家事が減った", False), ("連絡が取れず自然解約", False),
        ],
    },
    "unknown": {
        "criterion": "解約の理由が書かれていない、または不明",
        "rows": [
            ("", True), ("解約", True), ("本人希望", True), ("特になし", True), ("電話で解約の連絡あり", True),
            ("理由は聞けず", True), ("詳細不明", True), ("メールで終了希望とのみ", True), ("回答なし", True), ("担当が不在で聞き取れず", True),
            ("料金が高い", False), ("転居のため", False), ("スタッフ交代を機に", False), ("掃除の品質に不満", False), ("引越し", False),
            ("自分でやることにした", False), ("他社へ乗り換え", False), ("入院のため", False), ("家族の反対", False), ("利用頻度が減ったため", False),
        ],
    },
    "lost": {
        "criterion": "スタッフが迷子・乗り間違い・時間の間違いで遅刻または訪問できなかった",
        "rows": [
            ("駅を出て反対方向に歩き 20 分遅刻", True), ("乗換を間違え到着が遅れた", True), ("開始時間を 14 時と勘違い", True),
            ("住所が分からず客先に電話", True), ("バス停を間違えて遅刻", True), ("マンションの入口が分からず 10 分遅れ", True),
            ("別の日と勘違いして訪問せず", True), ("終点まで乗り過ごした", True), ("地図アプリの案内で迷い遅刻", True), ("開始時刻を 30 分早く認識し早く着きすぎた", True),
            ("体調不良で当日欠勤", False), ("電車遅延で遅刻（遅延証明あり）", False), ("鍵の受け渡しでトラブル", False), ("掃除の品質に苦情", False),
            ("お客様都合でキャンセル", False), ("寝坊で遅刻", False), ("前の現場が長引いて遅刻", False), ("道路渋滞で遅れ", False),
            ("持ち物を忘れて取りに戻り遅刻", False), ("シフト入力漏れで無断欠勤扱い", False),
        ],
    },
}


def run_batch(client: JevClient, name: str, s: dict) -> dict:
    rows = {f"r{i+1}": t for i, (t, _) in enumerate(s["rows"])}
    qs = {rid: question_for(rid) for rid in rows}
    r = client.ask({"context": CONTEXT, "criterion": s["criterion"], "rows": rows}, qs)
    out = []
    for i, (t, exp) in enumerate(s["rows"]):
        p = float(r["answers"][f"r{i+1}"]["noul"])
        out.append({"text": t, "expected": exp, "noul": p})
    return {"rows": out, "elapsed_ms": r["elapsed_ms"], "usage": r.get("usage")}


def run_single(client: JevClient, name: str, s: dict) -> dict:
    out, total = [], 0
    for t, exp in s["rows"]:
        r = client.ask({"context": CONTEXT, "criterion": s["criterion"], "rows": {"r1": t}}, {"r1": question_for("r1")})
        out.append({"text": t, "expected": exp, "noul": float(r["answers"]["r1"]["noul"])})
        total += r["elapsed_ms"]
    return {"rows": out, "elapsed_ms": total}


def summarize(rows: list) -> dict:
    pos = sorted(r["noul"] for r in rows if r["expected"])
    neg = sorted(r["noul"] for r in rows if not r["expected"])
    wrong = [(r["text"], r["expected"], r["noul"]) for r in rows if (r["noul"] >= 0.5) != r["expected"]]
    return {"min_true": pos[0], "max_false": neg[-1], "gap": round(pos[0] - neg[-1], 3), "wrong": wrong, "n": len(rows)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="vm_samples/jev_judge_batch_v1.json")
    ap.add_argument("--no-single", action="store_true")
    a = ap.parse_args()
    client = JevClient()
    out = {"context": CONTEXT, "question_template": question_for("rN"), "sets": {}}
    for name, s in SETS.items():
        print(f"\n== {name}: {s['criterion']} ==")
        b = run_batch(client, name, s)
        for r in b["rows"]:
            ok = (r["noul"] >= 0.5) == r["expected"]
            print(f"{'OK ' if ok else 'NG '} {r['noul']:.3f} {'T' if r['expected'] else 'F'}  {r['text'] or '（空）'}")
        b["summary"] = summarize(b["rows"])
        print(f"batch: {b['elapsed_ms']} ms, usage={b.get('usage')}, {b['summary']}")
        entry = {"criterion": s["criterion"], "batch": b}
        if not a.no_single:
            sg = run_single(client, name, s)
            sg["summary"] = summarize(sg["rows"])
            diffs = [(x["text"], x["noul"], y["noul"]) for x, y in zip(b["rows"], sg["rows"]) if abs(x["noul"] - y["noul"]) >= 0.2]
            print(f"single: {sg['elapsed_ms']} ms total, {sg['summary']}; |batch-single|>=0.2: {diffs}")
            entry["single"] = sg
        out["sets"][name] = entry
    p = Path(__file__).resolve().parent.parent / a.out
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("saved", p)


if __name__ == "__main__":
    main()
