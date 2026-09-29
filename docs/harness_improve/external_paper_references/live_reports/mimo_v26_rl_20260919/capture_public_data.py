"""归档直播页面实际使用的公开只读接口；端点来自已保存的 js/app.js。

仅用于本次调查的可复核快照，不抓取私有接口，不运行下载的脚本。
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
BASE = "https://mimo.xiaomi.com/rl/"
STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
OUT = ROOT / "snapshots" / STAMP
OUT.mkdir(parents=True, exist_ok=False)
manifest = []


def fetch(endpoint, name):
    url = BASE + endpoint
    started = datetime.now(timezone.utc).isoformat()
    with urlopen(url, timeout=45) as response:
        raw = response.read()
        headers = dict(response.headers)
    (OUT / name).write_bytes(raw)
    manifest.append({
        "url": url, "retrieved_at": started, "file": name,
        "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
        "headers": headers,
    })
    data = json.loads(raw)
    assert "error" not in data, (endpoint, data)
    return data


cfg = fetch("api/runs", "runs.json")
fetch("api/notices", "notices.json")
fetch("api/benchmarks", "benchmarks.json")
summaries = []
for run in cfg["runs"]:
    key = run["key"]
    status = fetch("api/status?" + urlencode({"run": key}), f"{key}_status_before.json")
    fetch("api/live?" + urlencode({"run": key}), f"{key}_live.json")
    version = status["version"]
    tags = fetch("api/tags?" + urlencode({"run": key, "v": version}), f"{key}_tags.json")
    chunks = [tags["tags"][i:i+96] for i in range(0, len(tags["tags"]), 96)]

    def get_chunk(item):
        i, chunk = item
        return fetch("api/series?" + urlencode({"run": key, "v": version, "tags": ",".join(chunk)}),
                     f"{key}_series_{i:02d}.json")

    with ThreadPoolExecutor(max_workers=4) as pool:
        parts = list(pool.map(get_chunk, enumerate(chunks)))
    merged = {k: v for k, v in parts[0].items() if k != "series"}
    merged["series"] = {}
    for part in parts:
        assert part["steps"] == merged["steps"], "快照跨 step，须重新采集"
        assert part["walls"] == merged["walls"], "快照跨运行时间轴，须重新采集"
        merged["series"].update(part["series"])
    assert set(merged["series"]) == set(tags["tags"]), "指标未完整归档"
    assert all(len(v) == len(merged["steps"]) for v in merged["series"].values() if v is not None)
    (OUT / f"{key}_series_merged.json").write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n")
    after = fetch("api/status?" + urlencode({"run": key}), f"{key}_status_after.json")
    summaries.append({"run": key, "label": run["label"], "tags": len(tags["tags"]),
                      "steps": merged["steps"], "version_before": version,
                      "version_after": after["version"], "stable": version == after["version"]})

(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
(OUT / "summary.json").write_text(json.dumps(summaries, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"snapshot": str(OUT.relative_to(ROOT)), "runs": summaries}, ensure_ascii=False, indent=2))
