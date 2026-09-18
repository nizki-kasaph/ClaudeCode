"""組み込み先 2（中止・指摘の検知）の Noul 質問文を、言い換え・引っかけ否定のサンプルで実測する。

使い方: python3 scripts/measure_stop_pushback.py [--out vm_samples/jev_stop_pushback_v1.json]
キーはリポジトリ直下の .env（TYPESAFE_API_KEY）。40 通で約 10 秒・約 0.5 円。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "client"))
from jev_client import JevClient  # noqa: E402

# ---- 質問文（プラグインへ Node で移すときはこの文言をそのまま使う） ----
STOP_CONTEXT = (
    "依頼者は社内チャットで AI アシスタント（Mugi）に作業を頼んでいる。"
    "Mugi はいまその作業を実行している最中で、`message` はその途中に依頼者が送った短い発言。"
)
STOP_QUESTION = {
    "type": "noul",
    "instructions": "`message` は、いま Mugi が実行中の作業を止めてほしいという依頼者の指示ですか？",
    "criteria": {
        "true": "実行中の作業をやめる・止める・中断する・これ以上やらない・そこまでで結構、と求めている",
        "false": (
            "続けるよう求めている（「止めずに続けて」「中止せずに」など）、"
            "中止・停止・キャンセルという言葉を別の話題（予定の中止、キャンセル料、停止中の設定の再開）で使っている、"
            "新しい依頼や質問、お礼、相づち"
        ),
    },
}

PUSHBACK_CONTEXT = (
    "依頼者は社内チャットで AI アシスタント（Mugi）に作業を頼み、Mugi から回答や結果を受け取ったところ。"
    "`message` はその直後に依頼者が送った発言。"
)
PUSHBACK_QUESTION = {
    "type": "noul",
    "instructions": "`message` で依頼者は、Mugi の直前の回答や結果が間違っている・期待と違う・不十分だと指摘していますか？",
    "criteria": {
        "true": "結果の誤り・食い違い・抜け・期待外れ・探し方の不足を指摘し、見直し・再確認・やり直しを求めている",
        "false": (
            "結果を受け入れている、お礼、次の新しい依頼、別の切り口や追加の分析を頼んでいる（誤りの指摘ではない）、"
            "「違い」「間違い」「期待」という言葉を別の意味で使っている、無関係な話題"
        ),
    },
}

# ---- サンプル（text, expected） ----
STOP_SAMPLES = [
    ("中止して", True),
    ("もういいです、止めてください", True),
    ("そこまでで結構です", True),
    ("今やってるの、やめてもらえますか", True),
    ("ストップ！", True),
    ("一旦止めて", True),
    ("作業を中断してください", True),
    ("もう大丈夫、続けなくていいよ", True),
    ("それ以上やらないで", True),
    ("ちょっと待って、実行しないで", True),
    ("中止せずに続けて", False),
    ("止めないで最後までやって", False),
    ("中止した予定を復活させて", False),
    ("昨日の会議は中止になりました", False),
    ("続けてください", False),
    ("ありがとう、助かりました", False),
    ("明日の予定を教えて", False),
    ("キャンセル料はいくらですか", False),
    ("途中でやめずに全部出して", False),
    ("停止中の cron を再開して", False),
]

PUSHBACK_SAMPLES = [
    ("それ違うよ", True),
    ("さっきの数字、合ってないと思う", True),
    ("結果が期待と違います", True),
    ("これ本当に正しい？先週は3件あったはず", True),
    ("その回答はズレてる", True),
    ("いや、そうじゃなくて", True),
    ("出力が抜けてます", True),
    ("石渡さんのはずが今野さんになってる", True),
    ("前回はできたのに今回はできてない", True),
    ("探し方が甘くない？", True),
    ("ありがとう、合ってます", False),
    ("次は先月分もお願い", False),
    ("違いがあれば教えて", False),
    ("間違い探しゲームをして", False),
    ("これで進めてください", False),
    ("昨日の議事録を出して", False),
    ("期待しています、よろしく", False),
    ("違う視点でも分析して", False),
    ("完璧です", False),
    ("前回と同じ形式で出して", False),
]


def run(client: JevClient, name: str, context: str, question: dict, samples: list) -> list:
    rows = []
    print(f"\n== {name} ==")
    for text, expected in samples:
        r = client.ask({"context": context, "message": text}, {name: question})
        p = float(r["answers"][name]["noul"])
        rows.append({"text": text, "expected": expected, "noul": p, "elapsed_ms": r["elapsed_ms"], "usage": r.get("usage")})
        mark = "OK " if (p >= 0.5) == expected else "NG "
        print(f"{mark} {p:.3f} {'T' if expected else 'F'}  {text}")
    return rows


def summarize(rows: list) -> dict:
    pos = sorted(r["noul"] for r in rows if r["expected"])
    neg = sorted(r["noul"] for r in rows if not r["expected"])
    return {"min_true": pos[0], "max_false": neg[-1], "gap": pos[0] - neg[-1], "n": len(rows)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="vm_samples/jev_stop_pushback_v1.json")
    a = ap.parse_args()
    client = JevClient()
    out = {
        "stop": {"context": STOP_CONTEXT, "question": STOP_QUESTION, "rows": run(client, "stop", STOP_CONTEXT, STOP_QUESTION, STOP_SAMPLES)},
        "pushback": {"context": PUSHBACK_CONTEXT, "question": PUSHBACK_QUESTION, "rows": run(client, "pushback", PUSHBACK_CONTEXT, PUSHBACK_QUESTION, PUSHBACK_SAMPLES)},
    }
    for k in ("stop", "pushback"):
        out[k]["summary"] = summarize(out[k]["rows"])
        print(k, out[k]["summary"])
    p = Path(__file__).resolve().parent.parent / a.out
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("saved", p)


if __name__ == "__main__":
    main()
