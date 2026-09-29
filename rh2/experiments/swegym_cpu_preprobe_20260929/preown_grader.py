"""把既有 grader 的前缀属主布置烘焙进新镜像；内容与模式不变才交付。

不修改正式保护脚本，不跳过运行时检查，也不改变actor镜像。只用于本批实际
已确认需要candidate UID54322可写的conda前缀；构建期慢操作只做一次。
"""
import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ns = ap.parse_args()
    out = Path(ns.out)
    out.mkdir(parents=True, exist_ok=False)
    base = json.loads(subprocess.check_output(["docker", "image", "inspect", ns.image], timeout=60))[0]
    (out / "base_inspect.json").write_text(json.dumps(base, indent=2) + "\n")
    context = out / "context"
    context.mkdir()
    # 只归一化tar中的属主：校验仍覆盖所有文件内容、模式、符号链接、路径与mtime。
    script = r'''set -euo pipefail
p=/opt/miniconda3/envs/testbed
test -d "$p"
fingerprint() { /bin/tar --sort=name --numeric-owner --owner=0 --group=0 --format=gnu -C "$p" -cf - . | /usr/bin/sha256sum | cut -d' ' -f1; }
before=$(fingerprint)
chown -R 54322:54322 -- "$p"
after=$(fingerprint)
printf 'RH2_PREOWN_BEFORE=%s\nRH2_PREOWN_AFTER=%s\n' "$before" "$after"
test "$before" = "$after"
unexpected=$(find "$p" \( -type f -o -type d \) \( ! -uid 54322 -o ! -gid 54322 \) -print -quit)
test -z "$unexpected"
printf 'RH2_PREOWN_FILES_DIRS_OK=1\n'
'''
    local_ref = "rh2-cpu29/preown-base:" + base["Id"].split(":")[1][:20]
    subprocess.run(["docker", "tag", base["Id"], local_ref], check=True, timeout=60)
    (context / "preown.sh").write_text(script)
    dockerfile = ("ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\n"
                  "COPY preown.sh /tmp/rh2-cpu29-preown.sh\n"
                  "RUN /bin/bash /tmp/rh2-cpu29-preown.sh && rm /tmp/rh2-cpu29-preown.sh\n")
    (context / "Dockerfile").write_text(dockerfile)
    tag = "rh2-cpu29/preowned-grader:" + base["Id"].split(":")[1][:20]
    started = time.time()
    with (out / "build.log").open("w") as log:
        p = subprocess.run(["docker", "build", "--pull=false", "--network=none", "--force-rm",
                            "--build-arg", "BASE_IMAGE=" + local_ref, "-t", tag, str(context)],
                           stdout=log, stderr=subprocess.STDOUT, timeout=2400)
    result = {"started_at": started, "finished_at": time.time(), "rc": p.returncode,
              "base_id": base["Id"], "scope": "grader prefix ownership only; actor unchanged",
              "dockerfile_sha256": hashlib.sha256(dockerfile.encode()).hexdigest(),
              "script_sha256": hashlib.sha256(script.encode()).hexdigest()}
    if p.returncode == 0:
        built = json.loads(subprocess.check_output(["docker", "image", "inspect", tag], timeout=60))[0]
        result.update(image_id=built["Id"], tag=tag,
                      base_layers_preserved=built["RootFS"]["Layers"][:len(base["RootFS"]["Layers"])] == base["RootFS"]["Layers"])
    (out / "image.json").write_text(json.dumps(result, indent=2) + "\n")
    if p.returncode or not result.get("base_layers_preserved"):
        raise RuntimeError("ownership layer build failed; retain original evidence and inspect build/container state")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
