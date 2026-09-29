"""在已有镜像的 CPU Docker 主机验证 Bash 激活时点；仅删除自己创建的容器。

不运行 CC、模型或正式 rollout；无需网络、私钥或凭据进入本脚本。
"""

import json
import subprocess
import uuid

IMAGE = "xingyaoww/sweb.eval.x86_64.conan-io_s_conan-15422:latest"


def docker(*args):
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=45, check=False)


def main():
    name = "rh2-codex-startup-home-" + uuid.uuid4().hex[:8]
    rows = []
    try:
        result = docker(
            "run", "-d", "--name", name, "--label", "rh2.review=startup_brief_20260923",
            "--network", "none", "--cap-drop", "ALL", "--cap-add", "CHOWN",
            "--cap-add", "DAC_OVERRIDE", "--cap-add", "FOWNER", "--memory", "512m",
            "--pids-limit", "64", IMAGE, "sleep", "90",
        )
        result.check_returncode()
        setup = """useradd -m -u 54321 -s /bin/bash agent && mkdir -p /rh2 && chmod 0755 /rh2 &&
cat > /rh2/bash_env <<'ENV'
printf 'ACTIVATION_HOME=%s\\n' "$HOME" >&2
source /opt/miniconda3/bin/activate testbed 2>/dev/null || true
ENV
chmod 0644 /rh2/bash_env
"""
        docker("exec", name, "bash", "-c", setup).check_returncode()
        command = (
            "cd /tmp && export HOME=/home/agent && "
            "python -B -S -c 'import sys;print(sys.executable)' && "
            "printf 'FINAL_HOME=%s\\n' \"$HOME\""
        )
        for label, env in (
            ("brief_shape", []),
            ("explicit_home", ["-e", "HOME=/home/agent"]),
            ("image_home_root_simulation", ["-e", "HOME=/root"]),
        ):
            result = docker("exec", "-u", "agent", "-e", "BASH_ENV=/rh2/bash_env", *env,
                            name, "bash", "-c", command)
            rows.append({"case": label, "code": result.returncode,
                         "stdout": result.stdout, "stderr": result.stderr})
    finally:
        cleanup = docker("rm", "-f", name)
    print(json.dumps({"image": IMAGE, "cases": rows, "cleanup_rc": cleanup.returncode}, indent=2))


if __name__ == "__main__":
    main()
