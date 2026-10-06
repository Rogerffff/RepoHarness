"""目标镜像内的私有警告观测；经cpu_slot run串行执行，不代替正式评分。"""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

IID = "scrapy__a95a338eeada7275a5289cf036136610ebaf07eb"
TEST_SHA = "sha256:9c6bc43ef5eead9453128d7d40959afb7bfd0d9e85c4c068a6d17993c991abac"


def docker(argv, timeout=60, check=True):
    result = subprocess.run(["docker", *argv], capture_output=True, text=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError("Docker operation failed: " + result.stderr[-1200:])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared-run", required=True)
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--tools", required=True)
    parser.add_argument("--capture-sha256", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    prepared, inputs, tools, out = map(Path, [args.prepared_run, args.inputs, args.tools, args.out])
    assert hashlib.sha256((tools / "capture_warning_records.py").read_bytes()).hexdigest() == args.capture_sha256
    facts = json.loads((prepared / "derived" / IID / "facts.json").read_text())
    assert facts["ok"] and facts["root_facts"]["tree"] == "e6f17ed8b7f80a0c0d6654f35d60e42bfd39a187f8c2442b854e388206349aeb"
    image = facts["derived_image_id"]
    inventory = json.loads((inputs / "input_inventory.json").read_text())
    digests = {item["path"]: item["sha256"] for item in inventory["files"]}
    out.mkdir(parents=True, exist_ok=False)
    records = []
    for candidate in ["C1", "C1_RuntimeWarning"]:
        patch = "candidates/" + candidate + ".patch"
        expected_patch = digests[patch]
        assert "sha256:" + hashlib.sha256((inputs / patch).read_bytes()).hexdigest() == expected_patch
        apply = ("from pathlib import Path;import hashlib,subprocess;"
                 "p=Path('/rh2_scrapy_inputs/" + patch + "');"
                 "assert 'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()==" + repr(expected_patch) + ";"
                 "subprocess.run(['git','apply','--check',str(p)],cwd='/testbed',check=True);"
                 "subprocess.run(['git','apply',str(p)],cwd='/testbed',check=True)")
        command = ("/testbed/.venv/bin/python -c " + __import__("shlex").quote(apply) + " && "
                   "/testbed/.venv/bin/python -W ignore /rh2_scrapy_tools/capture_warning_records.py "
                   "--test-file /rh2_private/r2e_tests/test_1.py --test-sha256 " + TEST_SHA)
        name = "scrapy-warnings-" + hashlib.sha256((args.run_id + candidate).encode()).hexdigest()[:16]
        cid = None
        row = {"candidate": candidate, "patch_sha256": expected_patch, "derived_image_id": image,
               "scope": "private_warning_observation_not_formal_grading", "container_name": name}
        try:
            cid = docker(["create", "--name", name, "--label", "rh2.run_id=" + args.run_id,
                          "--label", "rh2.package=r2e_scrapy", "--network", "none", "--cpus", "2",
                          "--memory", "4g", "--memory-swap", "4g", "--pids-limit", "512", "--user", "0",
                          "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--workdir", "/testbed",
                          "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "PYTHONWARNINGS=ignore::UserWarning,ignore::SyntaxWarning",
                          "--mount", "type=bind,src=" + str(inputs.resolve()) + ",dst=/rh2_scrapy_inputs,readonly",
                          "--mount", "type=bind,src=" + str(tools.resolve()) + ",dst=/rh2_scrapy_tools,readonly",
                          "--entrypoint", "bash", image, "-lc", command]).stdout.strip()
            assert re.fullmatch(r"[0-9a-f]{64}", cid), "只接受Docker返回的完整容器ID"
            inspected = json.loads(docker(["inspect", cid]).stdout)[0]
            assert inspected["Image"] == image and inspected["Config"]["Labels"]["rh2.run_id"] == args.run_id
            row["host_config"] = {k: inspected["HostConfig"][k] for k in ["NanoCpus", "Memory", "MemorySwap", "PidsLimit", "NetworkMode"]}
            result = docker(["start", "-a", cid], timeout=300, check=False)
            (out / (candidate + ".stdout.json")).write_text(result.stdout)
            (out / (candidate + ".stderr.log")).write_text(result.stderr)
            row["exit_code"] = result.returncode
            if result.returncode:
                raise RuntimeError(candidate + " observation failed; preserve raw output")
            report = json.loads(result.stdout)
            assert report["tests_run"] == 5 and not report["failures"] and not report["errors"]
            assert len(report["record_blocks"]) == 22 and report["filters_restored"]
            row["warning_count"] = sum(r["count"] for r in report["record_blocks"])
            row["warning_categories"] = sorted({w["category"] for r in report["record_blocks"] for w in r["warnings"]})
        finally:
            if cid:
                inspected = json.loads(docker(["inspect", cid]).stdout)[0]
                assert inspected["Config"]["Labels"]["rh2.run_id"] == args.run_id
                docker(["rm", "-f", cid])
                row["residual_after_cleanup"] = docker(["ps", "-a", "--filter", "id=" + cid, "--format", "{{.ID}}"]).stdout.strip()
                assert not row["residual_after_cleanup"]
            records.append(row)
            (out / "observation_summary.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"private_observations": records, "formal_acceptance": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
