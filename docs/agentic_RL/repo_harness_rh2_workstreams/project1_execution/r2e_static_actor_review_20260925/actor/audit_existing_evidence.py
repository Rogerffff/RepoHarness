"""只读重建首批 8 题 devcheck 的启动事实；本脚本不重新执行容器内命令。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


OUT = Path(__file__).resolve().parent
ROOT = next(p for p in OUT.parents if (p / "rh2/src/repoharness2").is_dir())
rows = []
for attempt in sorted((ROOT / "runs/r2e_actor_20260925/devcheck").glob("*/orig/attempt.json")):
    directory = attempt.parent
    record = json.loads(attempt.read_text())
    pre = json.loads((directory / "prelaunch.json").read_text())
    act = json.loads((directory / "activation_check.json").read_text())
    captures = {p.stem: p.read_text() for p in sorted((directory / "captures").glob("*.out"))}
    events = [json.loads(line) for line in (directory / "harness/trajectory.jsonl").read_text().splitlines() if line.strip()]
    inits = [e for e in events if e.get("type") == "system" and e.get("subtype") == "init"]
    results = [e for e in events if e.get("type") == "result"]
    tool_calls = [block for event in events if event.get("type") == "assistant"
                  for block in (event.get("message") or {}).get("content", []) if block.get("type") == "tool_use"]
    msg_starts = sum(e.get("type") == "stream_event" and (e.get("event") or {}).get("type") == "message_start" for e in events)
    source_files = [attempt, directory / "prelaunch.json", directory / "activation_check.json",
                    directory / "harness/trajectory.jsonl", *sorted((directory / "captures").glob("*.out"))]
    cleanup = record["cleanup"]
    command_rows = record["commands_result"]
    init_version = [e.get("claude_code_version") for e in inits]
    facts = pre["probe_facts"]
    row = {
        "task_id": record["task_id"], "evidence_dir": str(directory.relative_to(ROOT)),
        "overlay_image": record["overlay"]["derived_image_id"], "recipe_id": record["overlay"]["recipe_id"],
        "actual_image": pre["inspect_facts"]["image"],
        "all_image_observations_match": len({record["image"], record["overlay"]["derived_image_id"],
                                              pre["inspect_facts"]["image"], record["container_inspect"].split()[0]}) == 1,
        "head_is_public_base": facts["GIT_HEAD"] == record["base_commit"],
        "prelaunch_ok": pre["ok"], "uid": facts["UID"], "activation_write": facts["ACTIVATION_WRITE"],
        "activation_ok": act["ok"], "activation_facts": act["probe_facts"],
        "cpus": pre["inspect_facts"]["nano_cpus"] / 10**9, "memory_bytes": pre["inspect_facts"]["memory"],
        "r2e_preflight_raw": captures["r2e_preflight"].strip().splitlines(),
        "cc_versions": init_version, "cc_exit_code": record["harness_exit_code"],
        "cc_result_types": [e.get("subtype") for e in results], "bash_tool_count": sum(b["name"] == "Bash" for b in tool_calls),
        "command_count_including_preflight": len(command_rows),
        "all_command_captures_exist": all(r["id"] in captures for r in command_rows),
        "missing_or_timeout_commands": [r["id"] for r in command_rows if r["rc"] in (None, 124, 137)],
        "message_start_count": msg_starts, "stub_message_count": record["stub_counts_final"]["messages"],
        "author_checks_false": [k for k, v in record["checks"].items() if v is False],
        "cleanup_record_has_no_residue": all(not cleanup[k] for k in ("labeled_containers_left", "labeled_networks_left", "residual_after_force")),
        "raw_has_agent_uid": any("uid=54321(agent)" in value for value in captures.values()),
        "raw_has_declared_interpreter": any("RH2_SYS_EXECUTABLE=/testbed/.venv/bin/python" in value for value in captures.values()),
        "commands": [{k: r[k] for k in ("id", "rc", "status", "pytest")} for r in command_rows],
        "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files},
    }
    for key in ("all_image_observations_match", "head_is_public_base", "prelaunch_ok", "activation_ok", "all_command_captures_exist",
                "cleanup_record_has_no_residue", "raw_has_agent_uid", "raw_has_declared_interpreter"):
        assert row[key], (row["task_id"], key)
    assert row["uid"] == "54321" and row["activation_write"] == "DENIED"
    assert row["cc_versions"] == ["2.1.205"]
    assert row["message_start_count"] == row["stub_message_count"]
    assert row["bash_tool_count"] == row["command_count_including_preflight"]
    assert not row["missing_or_timeout_commands"]
    assert set(row["r2e_preflight_raw"]) == {"RH2_PREFLIGHT_INTERPRETER=ok", "RH2_PREFLIGHT_HIDDEN_TESTS=ok", "RH2_PREFLIGHT_GIT_HISTORY=ok"}
    rows.append(row)

assert len(rows) == 8
result = {
    "scope": "Read-only reconstruction of saved CPU/Claude Code stub evidence; not a new actor, Docker, Qwen adapter, or grader execution.",
    "task_count": len(rows), "commands_including_preflight": sum(r["command_count_including_preflight"] for r in rows),
    "rows": rows,
}
(OUT / "existing_evidence_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"task_count": len(rows), "commands_including_preflight": result["commands_including_preflight"],
                  "all_assertions_passed": True, "false_author_checks": {r["task_id"]: r["author_checks_false"] for r in rows if r["author_checks_false"]}}, ensure_ascii=False))
