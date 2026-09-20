"""OpenClaw プラグイン 4 件（シート意図・断言・承認要求・返答分類）の JEV 質問文を、言い換えサンプルで実測する。

使い方: python3 scripts/measure_jev_questions.py [--only sheet,assert,approval,reply] [--out vm_samples/jev_questions_v1.json]
キーはリポジトリ直下の .env（TYPESAFE_API_KEY）。80 件で約 20 秒・約 1 円。
質問文はここが正本。プラグイン（Node / Python）へは同じ文言を写す。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "client"))
from jev_client import JevClient  # noqa: E402

SETS: dict = {}

# ---- 1. シート出力の意図（scripts/session_intent.py）: state.messages は直近の依頼者発話（古い順） ----
SETS["sheet"] = {
    "kind": "noul",
    "state_key": "messages",
    "context": (
        "依頼者は社内チャットで AI アシスタント（Mugi）に社内台帳の検索や集計を頼んでいる。"
        "`messages` は直近の依頼者の発話（古い順）。Mugi は結果をチャットに表示するか、Google スプレッドシートなどのファイルに出力するかを選ぶ。"
    ),
    "question": {
        "type": "noul",
        "instructions": (
            "`messages` の依頼者は、結果をチャットに表示するだけでなく、スプレッドシート（Google シート）などのファイルとして"
            "出力・保存・共有することを求めていますか？出力先の名前が無くても、後から見返せる形で残す・置いておく・"
            "シートのタブごとに分ける、といった求めはファイル出力に当たります。"
        ),
        "criteria": {
            "true": "スプレッドシート・表ファイル・Drive やマイドライブへの保存・タブごとに分ける・後で見返せる／編集できる／共有できる形で残す、を求めている",
            "false": "チャットで見せる・読み上げる・件数だけ・口頭で済む程度のまとめ・シートについての質問や雑談・シートは要らないと言っている・出力先に触れていない依頼",
        },
    },
    "samples": [
        (["後で見返せる形で残しておいて"], True),
        (["これ、みんなで共有できるようにして"], True),
        (["一覧を Drive に置いといて"], True),
        (["ファイルにまとめてもらえる？"], True),
        (["タブごとに分けてほしい"], True),
        (["列に並べた形で保存して"], True),
        (["あとで編集できる形式にして"], True),
        (["マイドライブに入れておいて"], True),
        (["この結果、ファイルで頂戴"], True),
        (["先月の欠勤を出して", "それ、後で見返せるように残しておいて"], True),
        (["ここに表示して"], False),
        (["チャットで教えて"], False),
        (["件数だけ教えて"], False),
        (["シートの読み方を教えて"], False),
        (["スプレッドシートは要らない、ここで見せて"], False),
        (["明日の予定を教えて"], False),
        (["今の一覧を読み上げて"], False),
        (["ありがとう"], False),
        (["昨日のシート、誰が作った？"], False),
        (["先月の欠勤を出して", "口頭で説明できる程度にまとめて"], False),
    ],
}

# ---- 2. evidence-gate の断言判定: state.message は Mugi の返答 ----
SETS["assert"] = {
    "kind": "noul",
    "state_key": "message",
    "context": "`message` は AI アシスタント（Mugi）が社内の依頼者へ返した文。",
    "question": {
        "type": "noul",
        "instructions": "`message` で Mugi は、何かを実施・修正・送信・登録した、または原因を特定した、と既に済んだこととして断言していますか？",
        "criteria": {
            "true": "確認した・直した・送った・入れた・消した・反映した・終わっている・原因が分かった、など完了したこととして述べている",
            "false": "これから行う・まだ実行していない・止まった・できなかった・許可や選択を求めている・一覧や候補や結果を示しているだけ",
        },
    },
    "samples": [
        ("直しておきました", True),
        ("送っておいたよ🐾", True),
        ("もう入れてあります", True),
        ("原因が分かりました。権限不足でした", True),
        ("登録は終わっています", True),
        ("シートに書き込んであります", True),
        ("問題は解決済みです", True),
        ("該当の予定を消しました", True),
        ("反映させておいたので確認してください", True),
        ("調べたところ、設定が原因でした", True),
        ("これから確認します", False),
        ("確認してもよいですか", False),
        ("まだ実行していません", False),
        ("エラーで止まりました。どこまでやったか報告します", False),
        ("実行に必要な権限がありません", False),
        ("候補は 3 件です。どれにしますか", False),
        ("一覧はこちらです", False),
        ("ガードで止まったため実施できませんでした", False),
        ("承認をいただければ書き込みます", False),
        ("わかりました、進めますね", False),
    ],
}

# ---- 3. drive-url-guard の承認要求判定: state.message は Mugi の返答 ----
SETS["approval"] = {
    "kind": "noul",
    "state_key": "message",
    "context": (
        "`message` は AI アシスタント（Mugi）が社内の依頼者へ返した文。"
        "Mugi はスプレッドシートへ書き込む前にプレビューを見せて依頼者の承認を待つ決まりになっている。"
    ),
    "question": {
        "type": "noul",
        "instructions": "`message` で Mugi は、書き込みや実行の前に依頼者の承認・返事・判断を求めて待っていますか？",
        "criteria": {
            "true": "進めてよいか・問題ないか・どうするかを尋ね、依頼者の返事を待っている",
            "false": "既に書き込んだ・完了したと報告している、これから実行すると宣言している、結果や件数やエラーを伝えているだけ",
        },
    },
    "samples": [
        ("こちらの内容で書き込んでも大丈夫でしょうか", True),
        ("上の 3 件で問題なければ進めます", True),
        ("OK なら --confirm で実行します", True),
        ("この方向でよければ教えて", True),
        ("ゴーサインをください", True),
        ("内容を見て、進めるか決めてください", True),
        ("問題なければ書き込みます。どうしますか？", True),
        ("先に中身を見てもらえますか", True),
        ("書き込む前に一言ください", True),
        ("ここまでで合ってますか？", True),
        ("書き込みました。URL はこちらです", False),
        ("作成が完了しました", False),
        ("出力します", False),
        ("5 件見つかりました", False),
        ("エラーが出たので中断しました", False),
        ("シートを開いて確認しました", False),
        ("準備が整いました、いま書き込んでいます", False),
        ("以上です", False),
        ("該当はありませんでした", False),
        ("参考までにプレビューを貼ります。もう書き込み済みです", False),
    ],
}

# ---- 4. pinay-content-search の返答分類: state.message は依頼者の返答（概念の下書きを見せた直後） ----
SETS["reply"] = {
    "kind": "choice",
    "state_key": "message",
    "context": "依頼者は AI アシスタント（Mugi）が提案した検索語の一覧（概念の下書き）を見せられ、`message` で返答した。",
    "question": {
        "type": "choice",
        "instructions": "依頼者の返答 `message` はどれに当たりますか？",
        "criteria": {
            "confirm": "提案をそのまま承認している（それでいい・OK・進めて・登録して）",
            "add": "検索語を追加したい（〜も入れて・〜も対象に・〜も含めて）",
            "remove": "検索語を外したい（〜は要らない・〜は対象外・〜は含めないで）",
            "other": "上のどれでもない（質問・雑談・別件・中止・保留）",
        },
    },
    "samples": [
        ("それでいいよ", "confirm"),
        ("問題ないです", "confirm"),
        ("その語で探して", "confirm"),
        ("OKです、進めて", "confirm"),
        ("うん", "confirm"),
        ("『遅刻』も入れて", "add"),
        ("早退も対象にしたい", "add"),
        ("あと『無断』もお願い", "add"),
        ("欠勤だけじゃなく遅刻も", "add"),
        ("体調不良も含めてほしい", "add"),
        ("『休暇』は要らない", "remove"),
        ("有給は対象外にして", "remove"),
        ("『遅延』は外そう", "remove"),
        ("早退は別でいい", "remove"),
        ("体調不良は含めないで", "remove"),
        ("先週の件数は？", "other"),
        ("ありがとう", "other"),
        ("ちょっと待って", "other"),
        ("別の話だけど明日の予定は", "other"),
        ("中止", "other"),
    ],
}


def run(client: JevClient, name: str, s: dict) -> list:
    rows = []
    print(f"\n== {name} ==")
    for value, expected in s["samples"]:
        r = client.ask({"context": s["context"], s["state_key"]: value}, {name: s["question"]})
        ans = r["answers"][name]
        if s["kind"] == "noul":
            p = float(ans["noul"])
            ok = (p >= 0.5) == expected
            shown = f"{p:.3f} {'T' if expected else 'F'}"
            rows.append({"value": value, "expected": expected, "noul": p, "elapsed_ms": r["elapsed_ms"]})
        else:
            c = ans.get("choice")
            ok = c == expected
            shown = f"{c:>8} exp={expected}"
            rows.append({"value": value, "expected": expected, "choice": c, "raw": ans, "elapsed_ms": r["elapsed_ms"]})
        print(f"{'OK ' if ok else 'NG '} {shown}  {value}")
    return rows


def summarize(kind: str, rows: list) -> dict:
    if kind == "noul":
        pos = sorted(r["noul"] for r in rows if r["expected"])
        neg = sorted(r["noul"] for r in rows if not r["expected"])
        return {"min_true": pos[0], "max_false": neg[-1], "gap": round(pos[0] - neg[-1], 3), "n": len(rows)}
    wrong = [r for r in rows if r["choice"] != r["expected"]]
    return {"correct": len(rows) - len(wrong), "n": len(rows), "wrong": [(r["value"], r["expected"], r["choice"]) for r in wrong]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default="vm_samples/jev_questions_v1.json")
    a = ap.parse_args()
    names = [n for n in a.only.split(",") if n] or list(SETS)
    client = JevClient()
    out = {}
    for n in names:
        s = SETS[n]
        rows = run(client, n, s)
        out[n] = {"context": s["context"], "question": s["question"], "rows": rows, "summary": summarize(s["kind"], rows)}
        print(n, out[n]["summary"])
    p = Path(__file__).resolve().parent.parent / a.out
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("saved", p)


if __name__ == "__main__":
    main()
