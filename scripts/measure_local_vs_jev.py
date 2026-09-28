"""ローカル LLM（Ollama）と JEV を同じデータで測り、しきい値判定の一致率を出す（2026-09-29・手順 A-4）。

使い方: python3 scripts/measure_local_vs_jev.py [--sets stop,pushback,sheet,assert,approval,reply] [--model gemma4:e4b]
        [--jev live|cached] [--out vm_samples/local_vs_jev_<model>.json]
  - データと質問文は measure_stop_pushback.py（stop / pushback）と measure_jev_questions.py（sheet / assert / approval / reply）の正本をそのまま使う。
  - JEV 側は --jev live で TypeSafe に投げ直す（80〜120 件で約 1 円）。--jev cached は vm_samples/jev_stop_pushback_v1.json と
    vm_samples/jev_questions_v1.json の保存値を使う（無ければ live に落ちる）。
  - 一致率は「期待値との正誤（0.5 しきい値）」と「JEV とローカルの判定一致」の 2 つ。Choice は choice の一致。
  - M1 の E4B の数値は配線確認用で採用判断には使わない。M5 では --model gemma4:26b-a4b で同じデータを回し、ここで初めて置換可否を判断する。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "client"))
sys.path.insert(0, str(ROOT / "scripts"))
from jev_client import JevClient  # noqa: E402
import measure_stop_pushback as msp  # noqa: E402
import measure_jev_questions as mjq  # noqa: E402


def build_sets() -> dict:
    """{name: {"kind", "context", "question", "state_key", "samples": [(state_value, expected)]}}"""
    sets = {
        "stop": {"kind": "noul", "context": msp.STOP_CONTEXT, "question": msp.STOP_QUESTION, "state_key": "message", "samples": msp.STOP_SAMPLES},
        "pushback": {"kind": "noul", "context": msp.PUSHBACK_CONTEXT, "question": msp.PUSHBACK_QUESTION, "state_key": "message", "samples": msp.PUSHBACK_SAMPLES},
    }
    for name, s in mjq.SETS.items():
        sets[name] = {"kind": s["kind"], "context": s["context"], "question": s["question"], "state_key": s["state_key"], "samples": s["samples"]}
    return sets


def ask_one(client: JevClient, name: str, s: dict, value) -> dict:
    r = client.ask({"context": s["context"], s["state_key"]: value}, {name: s["question"]})
    ans = r["answers"][name]
    if s["kind"] == "noul":
        return {"noul": float(ans["noul"]), "elapsed_ms": r["elapsed_ms"]}
    return {"choice": ans.get("choice"), "confidence": float(ans.get("confidence") or 0), "elapsed_ms": r["elapsed_ms"]}


def cached_jev(name: str, s: dict) -> dict | None:
    """保存済みの JEV 結果を {json.dumps(value): row} で返す。無ければ None。"""
    paths = {"stop": "jev_stop_pushback_v1.json", "pushback": "jev_stop_pushback_v1.json"}
    p = ROOT / "vm_samples" / paths.get(name, "jev_questions_v1.json")
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    block = data.get(name)
    if not block:
        return None
    out = {}
    for row in block.get("rows", []):
        key = json.dumps(row.get("text", row.get("state", row.get("messages"))), ensure_ascii=False)
        out[key] = row
    return out


def judge(kind: str, row: dict, expected) -> bool:
    if kind == "noul":
        return (row["noul"] >= 0.5) == bool(expected)
    return row.get("choice") == expected


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", default="stop,pushback,sheet,assert,approval,reply")
    ap.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "gemma4:e4b"))
    ap.add_argument("--jev", choices=["live", "cached"], default="live")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    os.environ["OLLAMA_MODEL"] = a.model
    local = JevClient(backend="ollama")
    jev = JevClient(backend="typesafe") if a.jev == "live" or True else None
    sets = build_sets()
    result = {"model": a.model, "jev": a.jev, "sets": {}}
    for name in [x.strip() for x in a.sets.split(",") if x.strip()]:
        s = sets[name]
        cache = cached_jev(name, s) if a.jev == "cached" else None
        rows = []
        print(f"\n== {name} ({s['kind']}, {len(s['samples'])} 件) ==")
        t0 = time.perf_counter()
        for value, expected in s["samples"]:
            lr = ask_one(local, name, s, value)
            key = json.dumps(value, ensure_ascii=False)
            if cache and key in cache and ("noul" in cache[key] or "choice" in cache[key]):
                c = cache[key]
                jr = {"noul": float(c["noul"]), "elapsed_ms": c.get("elapsed_ms")} if s["kind"] == "noul" else {"choice": c.get("choice"), "confidence": float(c.get("confidence") or 0), "elapsed_ms": c.get("elapsed_ms")}
            else:
                jr = ask_one(jev, name, s, value)
            row = {"value": value, "expected": expected, "local": lr, "jev": jr,
                   "local_ok": judge(s["kind"], lr, expected), "jev_ok": judge(s["kind"], jr, expected)}
            row["agree"] = (lr.get("noul", 0) >= 0.5) == (jr.get("noul", 0) >= 0.5) if s["kind"] == "noul" else lr.get("choice") == jr.get("choice")
            rows.append(row)
            lv = f"{lr['noul']:.2f}" if s["kind"] == "noul" else f"{lr.get('choice')}({lr['confidence']:.2f})"
            jv = f"{jr['noul']:.2f}" if s["kind"] == "noul" else f"{jr.get('choice')}({jr['confidence']:.2f})"
            mark = ("L" if row["local_ok"] else "l") + ("J" if row["jev_ok"] else "j") + ("=" if row["agree"] else "≠")
            print(f"{mark} local={lv:>14} jev={jv:>14} exp={expected!s:>6}  {str(value)[:40]}")
        n = len(rows)
        summary = {
            "n": n,
            "local_accuracy": round(sum(r["local_ok"] for r in rows) / n, 3),
            "jev_accuracy": round(sum(r["jev_ok"] for r in rows) / n, 3),
            "agreement": round(sum(r["agree"] for r in rows) / n, 3),
            "local_ms_avg": round(sum(r["local"]["elapsed_ms"] for r in rows) / n),
            "jev_ms_avg": round(sum((r["jev"]["elapsed_ms"] or 0) for r in rows) / n),
            "wall_s": round(time.perf_counter() - t0, 1),
        }
        print(name, summary)
        result["sets"][name] = {"kind": s["kind"], "summary": summary, "rows": rows}
    out = Path(a.out) if a.out else ROOT / "vm_samples" / f"local_vs_jev_{a.model.replace(':', '_').replace('/', '_')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nsaved", out)
    print("\n| set | n | local 正答 | JEV 正答 | 一致率 | local ms | JEV ms |\n|---|---|---|---|---|---|---|")
    for name, s in result["sets"].items():
        m = s["summary"]
        print(f"| {name} | {m['n']} | {m['local_accuracy']:.0%} | {m['jev_accuracy']:.0%} | {m['agreement']:.0%} | {m['local_ms_avg']} | {m['jev_ms_avg']} |")


if __name__ == "__main__":
    main()
