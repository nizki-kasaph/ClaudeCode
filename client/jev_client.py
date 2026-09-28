"""JEV（TypeSafe 判定専用モデル）の最小クライアント。

経路は環境変数で切り替える。
  JEV_BACKEND=typesafe（既定）   … TypeSafe 公式 API（2026-09-19 実測済み。日本から 200〜270 ms、初回のみ約 600 ms）
      TYPESAFE_API_KEY が必要
  JEV_BACKEND=cloudflare          … Cloudflare Workers AI REST
      CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN が必要。AI Gateway クレジット（前払い）が無いと 402
  JEV_BACKEND=ollama              … ローカル LLM（Ollama ネイティブ API /api/chat、JSON 構造化出力）に JEV と同じ質問形式で答えさせる
      OLLAMA_BASE_URL（既定 http://127.0.0.1:11434）/ OLLAMA_MODEL（既定 gemma4:e4b）。キー不要。
      配線確認と JEV との一致率の実測用（2026-09-29 手順 A-4）。noul は「true である確率」を JSON で答えさせた値で、
      JEV の校正された確率とは意味が違う（しきい値の一致率だけを見る）。M1 の E4B の数値は採用判断に使わない。
      対応する型は noul / choice。score / 他の型は {"error": "unsupported"} を返す。

質問の書式は docs/jev-usage-guide.md §5 の生 JSON と同じ。
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

# 第三者モデルは URL にモデル名を入れず、本文 {"model","input"} で /ai/run に投げる（2026-09-19 実測）
CF_URL = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run"
CF_MODEL = "typesafe/jev"
TS_URL = "https://api.typesafe.ai/v1/systemone"
OLLAMA_URL_DEFAULT = "http://127.0.0.1:11434"
OLLAMA_MODEL_DEFAULT = "gemma4:e4b"

# ローカル LLM に JEV の質問を答えさせるときの固定文（変えるときは measure_local_vs_jev.py で一致率を取り直す）
OLLAMA_SYSTEM = (
    "あなたは判定器です。与えられた state（JSON）について question に答え、指定された JSON だけを出力します。"
    "根拠は state の中だけに求め、推測で事実を足しません。"
)
NOUL_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "boolean"}, "probability": {"type": "number"}},
    "required": ["answer", "probability"],
}


def load_env(path: Optional[Path] = None) -> None:
    """リポジトリ直下の .env を読み、未設定の環境変数だけ埋める。"""
    env_path = path or Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _choice_schema(keys: list) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {"choice": {"type": "string", "enum": keys}, "confidence": {"type": "number"}},
        "required": ["choice", "confidence"],
    }


class JevClient:
    def __init__(self, backend: Optional[str] = None, timeout: float = 30.0) -> None:
        load_env()
        self.backend = (backend or os.getenv("JEV_BACKEND", "typesafe")).lower()
        self.timeout = timeout
        self.session = requests.Session()  # 接続を使い回す（往復 0.3 秒の節約）
        self.ollama_model = ""
        if self.backend == "cloudflare":
            account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
            self.url = CF_URL.format(account_id=account_id)
            token = os.environ["CLOUDFLARE_API_TOKEN"]
        elif self.backend == "typesafe":
            self.url = TS_URL
            token = os.environ["TYPESAFE_API_KEY"]
        elif self.backend == "ollama":
            self.url = os.getenv("OLLAMA_BASE_URL", OLLAMA_URL_DEFAULT).rstrip("/")
            self.ollama_model = os.getenv("OLLAMA_MODEL", OLLAMA_MODEL_DEFAULT)
            self.timeout = max(timeout, 180.0)  # 起動直後の読み込み（M1 で 8 秒）と長文の処理（41 tok/s）を見込む
            self.session.headers.update({"Content-Type": "application/json"})
            return
        else:
            raise ValueError(f"unknown JEV_BACKEND: {self.backend}")
        self.session.headers.update(
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )

    def ask(self, state: Any, questions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """state と questions を投げ、{model, answers, usage, elapsed_ms} を返す。

        同じ state への質問は 1 回にまとめて渡すこと（往復回数が支配的）。
        """
        if self.backend == "ollama":
            return self._ask_ollama(state, questions)
        if self.backend == "cloudflare":
            body: Dict[str, Any] = {"model": CF_MODEL, "input": {"state": state, "questions": questions}}
        else:
            body = {"model": os.getenv("JEV_MODEL", "jev-latest"), "state": state, "questions": questions}
        t0 = time.perf_counter()
        resp = self.session.post(self.url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), timeout=self.timeout)
        elapsed_ms = round((time.perf_counter() - t0) * 1000)
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
        # Cloudflare 経由は {success, result: {...}} に包まれる（記事 §5 の r.result ?? r と同じ扱い）
        if self.backend == "cloudflare":
            if not data.get("success", True):
                raise RuntimeError(f"Cloudflare error: {data.get('errors')}")
            data = data.get("result", data)
        data["elapsed_ms"] = elapsed_ms
        return data

    # ---- ローカル LLM（Ollama）で JEV の質問形式を代行 ----
    def _ask_ollama(self, state: Any, questions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """質問ごとに 1 回 /api/chat を叩く（構造化出力）。答えは JEV と同じ形 {name: {"noul": p}} / {"choice", "confidence"}。"""
        t0 = time.perf_counter()
        answers: Dict[str, Any] = {}
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0}
        for name, q in questions.items():
            qtype = str(q.get("type", "noul")).lower()
            payload = {"state": state, "question": {k: v for k, v in q.items() if k != "type"}}
            if qtype == "noul":
                schema = NOUL_SCHEMA
                fmt = "出力: {\"answer\": true か false, \"probability\": question の答えが true である確率（0〜1 の小数）}"
            elif qtype == "choice":
                keys = list((q.get("criteria") or {}).keys())
                if not keys:
                    answers[name] = {"error": "choice には criteria が必要"}
                    continue
                schema = _choice_schema(keys)
                fmt = "出力: {\"choice\": criteria のキーのうち最も当てはまる 1 つ, \"confidence\": その確信度（0〜1 の小数）}"
            else:
                answers[name] = {"error": "unsupported", "type": qtype}
                continue
            user = json.dumps(payload, ensure_ascii=False) + "\n\n" + fmt
            body = {
                "model": self.ollama_model,
                "messages": [{"role": "system", "content": OLLAMA_SYSTEM}, {"role": "user", "content": user}],
                "stream": False,
                "think": False,
                "format": schema,
                "keep_alive": "15m",
                "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 200},
            }
            resp = self.session.post(f"{self.url}/api/chat", data=json.dumps(body, ensure_ascii=False).encode("utf-8"), timeout=self.timeout)
            if resp.status_code >= 400:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:500]}")
            data = resp.json()
            usage["calls"] += 1
            usage["prompt_tokens"] += int(data.get("prompt_eval_count") or 0)
            usage["completion_tokens"] += int(data.get("eval_count") or 0)
            content = (data.get("message") or {}).get("content") or ""
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                answers[name] = {"error": "malformed", "raw": content[:200]}
                continue
            if qtype == "noul":
                p = float(parsed.get("probability", 0.5))
                ans = parsed.get("answer")
                # 「true である確率」を「答えの確率」と取り違える出力を整合させる（answer=false で p>0.5 など）
                if ans is False and p > 0.5:
                    p = 1.0 - p
                elif ans is True and p < 0.5:
                    p = 1.0 - p
                answers[name] = {"type": "noul", "noul": round(min(max(p, 0.0), 1.0), 4), "answer": bool(ans)}
            else:
                conf = float(parsed.get("confidence", 0.0))
                answers[name] = {"type": "choice", "choice": str(parsed.get("choice", "")), "confidence": round(min(max(conf, 0.0), 1.0), 4), "probabilities": None}
        return {
            "model": f"ollama/{self.ollama_model}",
            "answers": answers,
            "usage": usage,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000),
        }


if __name__ == "__main__":
    # 記事 §5 のメール判定の例をそのまま投げる
    client = JevClient()
    result = client.ask(
        state="決済が3日間ずっと失敗しています！至急対応してください。",
        questions={
            "is_urgent": {"type": "noul", "instructions": "このメッセージは緊急性を伝えていますか？"},
            "department": {
                "type": "choice",
                "instructions": "どのチームが対応すべきですか？",
                "criteria": {"billing": "支払い・請求・返金", "technical": "不具合・障害・連携", "sales": "料金プラン・新規契約"},
            },
            "frustration": {
                "type": "score",
                "instructions": "顧客はどのくらい苛立っていますか？",
                "criteria": ["落ち着いている", "不満がある", "激怒している"],
            },
        },
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
