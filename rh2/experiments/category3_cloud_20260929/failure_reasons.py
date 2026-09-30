"""汇总一个正式评分目录（runs/ 下的 formal*/）中每个候选的结果与失败位置，写成 failure_reasons.txt 的格式。

每行：候选名、reward、F2P、参考缺席数、补丁是否应用、安装末命令 RC、测试 RC、清理、候选补丁 sha 前缀，
以及评分日志里第一个失败测试的位置：测试文件中的各帧（test=，由外到内，如调用处>helper 断言行）、最内层帧（inner=）与该段第一条 E 行。
只读账本与评分日志，不改任何文件。用法：python failure_reasons.py <formal 目录> [> failure_reasons.txt]
"""
import json
import re
import sys
from pathlib import Path

HEADER = re.compile(r"^_{3,} (\S.*?) _{3,}$")
FRAME = re.compile(r"^(\S+\.py):(\d+): ")


def first_failure(log_text):
    section, frames, e_line = None, [], None
    for line in log_text.splitlines():
        m = HEADER.match(line)
        if m:
            if section and (frames or e_line):
                break
            section, frames, e_line = m.group(1), [], None
            continue
        if section is None:
            continue
        m = FRAME.match(line)
        if m:
            frames.append((m.group(1), int(m.group(2))))
        elif line.startswith("E ") and e_line is None:
            e_line = line[1:].strip()
    if not section:
        return ""
    test_frames = [f for f in frames if "test" in Path(f[0]).name]
    # 测试文件中的全部帧，由外到内（例如 F2P 调用处 > 模块级 helper 中的断言行）
    test = (Path(test_frames[0][0]).name + ":" + ">".join(str(f[1]) for f in test_frames)) if test_frames else "-"
    inner = f"{Path(frames[-1][0]).name}:{frames[-1][1]}" if frames else "-"
    return f"[{section}] test={test} inner={inner} E: {(e_line or '')[:160]}"


def main(formal_dir):
    formal_dir = Path(formal_dir)
    for ledger in sorted(formal_dir.glob("ledger_*.jsonl")):
        name = ledger.name[len("ledger_"):-len(".jsonl")]
        rec = json.loads(ledger.read_text().splitlines()[-1])
        rep = rec.get("report") or {}
        cand = rec.get("candidate") or {}
        sha = (cand.get("patch_sha256") or "-").split(":")[-1][:8]
        install = rec.get("install") or {}
        test = rec.get("test") or {}
        applied = cand.get("apply_stderr_tail") is None
        log_path = Path((rec.get("log") or {}).get("path") or "")
        local = formal_dir / "eval_logs" / log_path.name
        reason = ""
        if rep.get("reward") != 1.0 and local.is_file():
            reason = first_failure(local.read_text(errors="replace"))
        print(f"{name:<28} reward={rep.get('reward')} f2p={rep.get('f2p_pass')}/{rep.get('f2p_total')} "
              f"p2p_fail={rep.get('p2p_fail')}/{rep.get('p2p_total')} missing={rec.get('reference_missing_count')} "
              f"apply={applied} install_rc={install.get('install_rc_last_command')} test_rc={test.get('rc')} "
              f"cleanup={(rec.get('cleanup') or {}).get('removed')} sha={sha} {reason}".rstrip())


if __name__ == "__main__":
    main(sys.argv[1])
