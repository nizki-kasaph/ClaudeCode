"""line-asana-triage が Asana に起票した [AI自動起票] タスクを読み取り、実測用データ（元テキスト・区分・題名・詳細）にする。
使い方: cd ~/Documents/Claude/LineAsanaTriage && python3 ~/Documents/Claude/JEV-UsageGuide/scripts/pull_triage_tasks.py <出力ディレクトリ>
（LineAsanaTriage/.env の ASANA_API_TOKEN / ASANA_PROJECT_GID を使う。読み取りのみ。出力は git 除外の vm_samples/ に置く）"""
import json
import os
import re
import sys

import requests
from dotenv import load_dotenv

load_dotenv(".env")
tok = os.getenv("ASANA_API_TOKEN")
proj = os.getenv("ASANA_PROJECT_GID")
h = {"Authorization": f"Bearer {tok}"}
out = []
url = f"https://app.asana.com/api/1.0/projects/{proj}/tasks"
params = {"opt_fields": "name,notes,created_at,completed,memberships.section.name", "limit": 100}
while url:
    r = requests.get(url, headers=h, params=params, timeout=30)
    r.raise_for_status()
    j = r.json()
    for t in j["data"]:
        if not t["name"].startswith("[AI自動起票]"):
            continue
        m = re.match(r"\[AI自動起票\]\[(.+?)\]\s*(.*)", t["name"])
        notes = t.get("notes") or ""
        src = notes.split("【元テキスト】", 1)[1].strip() if "【元テキスト】" in notes else ""
        desc = re.search(r"【詳細内容】\n(.*?)\n\n---", notes, re.S)
        out.append({
            "gid": t["gid"], "created_at": t["created_at"],
            "category": m.group(1) if m else "", "title": m.group(2) if m else t["name"],
            "description": desc.group(1).strip() if desc else "", "source": src,
            "section": (t.get("memberships") or [{}])[0].get("section", {}).get("name", ""),
        })
    nxt = j.get("next_page")
    url = nxt["uri"] if nxt else None
    params = None
os.makedirs(sys.argv[1], exist_ok=True)
json.dump(out, open(os.path.join(sys.argv[1], "triage_tasks.json"), "w"), ensure_ascii=False, indent=1)
print("tasks", len(out))
