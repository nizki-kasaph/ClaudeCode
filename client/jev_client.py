"""JEV（TypeSafe 判定専用モデル）の最小クライアント。

経路は環境変数で切り替える。
  JEV_BACKEND=cloudflare（既定） … Cloudflare Workers AI REST
      CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN が必要
  JEV_BACKEND=typesafe            … TypeSafe 公式 API
      TYPESAFE_API_KEY が必要（早期アクセス招待後）

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


class JevClient:
    def __init__(self, backend: Optional[str] = None, timeout: float = 30.0) -> None:
        load_env()
        self.backend = (backend or os.getenv("JEV_BACKEND", "cloudflare")).lower()
        self.timeout = timeout
        self.session = requests.Session()  # 接続を使い回す（往復 0.3 秒の節約）
        if self.backend == "cloudflare":
            account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
            self.url = CF_URL.format(account_id=account_id)
            token = os.environ["CLOUDFLARE_API_TOKEN"]
        elif self.backend == "typesafe":
            self.url = TS_URL
            token = os.environ["TYPESAFE_API_KEY"]
        else:
            raise ValueError(f"unknown JEV_BACKEND: {self.backend}")
        self.session.headers.update(
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )

    def ask(self, state: Any, questions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """state と questions を投げ、{model, answers, usage, elapsed_ms} を返す。

        同じ state への質問は 1 回にまとめて渡すこと（往復回数が支配的）。
        """
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
