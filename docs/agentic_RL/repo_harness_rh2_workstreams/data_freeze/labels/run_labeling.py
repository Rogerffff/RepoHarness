#!/usr/bin/env python3
"""DF-4 打标 runner：对输入 jsonl 逐题调 claude headless，输出标签 jsonl。
用法: python3 run_labeling.py <in.jsonl> <out.jsonl>
"""
import json
import subprocess
import sys
import time
from pathlib import Path

TEMPLATE = """你是软件工程任务质量审计员。给定一个 GitHub issue 修复任务的题面，输出三个质量标签和一个泄漏判定。只依据给定文本判断，不要臆测仓库内容。

【题面开始】
{problem_statement}
【题面结束】
【issue 评论区（仅用于泄漏判定）开始】
{hints_text}
【issue 评论区结束】

按以下定义逐项判定：

1. issue_clarity（题意清晰度）：
   pass = 明确说了"什么行为错了/期望什么行为"，有可操作的复现或定位线索（报错信息、代码片段、具体 API 名、复现步骤任一即可）。
   warn = 能看懂要修什么，但缺复现线索或期望行为表述含糊，需要 agent 自行猜测边界。
   fail = 题面含糊到无法确定改什么（如只有一句抱怨、断链引用、或需要外部上下文才能理解）。

2. test_adequacy（可验证性，仅从题面推断）：
   pass = 题面描述的是可被测试断言的具体行为差异（错误输出/异常/返回值）。
   warn = 行为差异存在但边界模糊（如"性能更好""更合理"），测试可能只覆盖狭窄实现细节。
   fail = 题面诉求本质上不可由自动测试判定（纯风格/文档/主观体验）。

3. solution_leakage（解法泄漏，题面 + 评论区一起判）：
   pass = 无解法信息。注意：需求本体（期望的接口形态、期望的输出/错误消息文本）不算泄漏。
   warn = 有实现方向提示（指出了大概哪个函数/模块该改怎么改，或给出行为级答案但无源码 diff）。
   fail = 含直接答案：完整/部分修复代码或 diff、逐行改法描述、指向修复 commit/PR 的 URL 或 hash、"Fixes #N 已在 X 修复"类表述。

4. leakage_evidence：若 solution_leakage 非 pass，摘录触发判定的原文片段（≤200 字符）；否则 null。

输出（严格 JSON 一行，无其他任何文字）：
{{"issue_clarity": "...", "clarity_reason": "≤50字", "test_adequacy": "...", "adequacy_reason": "≤50字", "solution_leakage": "...", "leakage_reason": "≤50字", "leakage_evidence": "... 或 null"}}"""


def label_one(row):
    prompt = TEMPLATE.format(
        problem_statement=(row.get("problem_statement") or "")[:12000],
        hints_text=(row.get("hints_text") or "")[:4000] or "(空)",
    )
    r = subprocess.run(
        ["claude", "-p", "--output-format", "text"],
        input=prompt, capture_output=True, text=True, timeout=300,
    )
    out = r.stdout.strip()
    start, end = out.find("{"), out.rfind("}")
    if start == -1 or end <= start:
        return {"_error": "no_json", "_raw": out[:500]}
    try:
        return json.loads(out[start : end + 1])
    except json.JSONDecodeError:
        return {"_error": "bad_json", "_raw": out[start : start + 500]}


def main():
    src, dst = sys.argv[1], sys.argv[2]
    done = set()
    if Path(dst).exists():  # 断点续跑
        for line in Path(dst).read_text().splitlines():
            if line.strip():
                done.add(json.loads(line)["instance_id"])
    rows = [json.loads(l) for l in Path(src).read_text().splitlines()]
    with open(dst, "a") as f:
        for i, row in enumerate(rows):
            iid = row.get("instance_id") or row.get("repo_name") + "@" + row.get("commit_hash", "")[:12]
            if iid in done:
                continue
            t0 = time.time()
            result = label_one(row)
            result["instance_id"] = iid
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
            f.flush()
            status = "ERR" if "_error" in result else "ok"
            print(f"[{i+1}/{len(rows)}] {iid} {status} {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
