"""pydantic-8316 独立复核者自造候选（2026-09-30，不继承作者上下文）。
做法同作者 make_candidates.py：只替换 base `pydantic/alias_generators.py` 中 `to_snake` 的函数体（docstring 之后），
输出 <name>.patch（git 风格 a/ b/ 前缀）。按公开要求判对错，不以 gold 为答案。
用法：python make_review_candidates.py <base_alias_generators.py> <out_dir>

合理实现（查 v2 与复核草案是否误拒，均与 gold 和作者 5 个合理实现写法不同）：
  rv_tokens      正则分词再拼接（不是逐处插下划线）；数字按 base 读法（A1 -> a_1）；非 ASCII 字符原样保留、不参与断开
  rv_scan_gold   逐字符扫描、用 str.isupper/islower（Unicode 感知）；数字按 gold 读法（A1 -> a1）
  rv_split_join  re.split 零宽边界再 '_'.join；数字按 gold 读法
  rv_acr_min2    gold 写法但缩写至少 2 个字母（XAxis、getAValue 不拆：单字母词有 OAuth/IPhone 式歧义，属未规定行为）
错误候选（查漏判；每个都在某个“缩写＋单词”实例上违反题面一般要求）：
  阈值：w_acr_max8（只认 1–8 个字母的缩写）、w_count2（缩写规则只替换前两处）、w_len_cap（输入超过 20 个字符就沿用 base 算法）
  位置：w_window8（缩写起点在前 8 个字符内才拆）、w_mid_underscore（先剥前后下划线；中段的缩写只在串首或小写字母/数字之后才拆，
        串中下划线之后的缩写不拆）、w_last_only（只拆最后一个缩写，依赖出现次序）
  编码子集：w_skip_nonascii（输入含非 ASCII 字符就沿用 base 算法）
  示例字面值（退化探测）：w_example_only（只特判题面原例 HTTPResponse）
"""
import difflib
import sys
from pathlib import Path

BASE_BODY = """    snake = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
    snake = re.sub(r'([a-z0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    return snake.lower()
"""

# gold 的四条规则，供若干错误候选复用（只改其中一处，便于看清“错在哪里”）
GOLD_RULES_AFTER_ACRONYM = """    snake = re.sub(r'([a-z])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    snake = re.sub(r'([0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    snake = re.sub(r'([a-z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    return snake.lower()
"""

BASE_ALGO = """        snake = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
        snake = re.sub(r'([a-z0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
        return snake.lower()
"""

BODIES = {
    # ---- 合理实现 ----
    "rv_tokens": """    # tokenize into words (an acronym is a run of capitals not followed by a lowercase letter), then join with '_'
    tokens = re.findall(r'_+|[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+|[^A-Za-z0-9_]+', camel)
    out = []
    for tok in tokens:
        if out and re.match(r'[A-Za-z0-9]', tok) and re.search(r'[A-Za-z0-9]$', out[-1]):
            out.append('_')
        out.append(tok)
    return ''.join(out).lower()
""",
    "rv_scan_gold": """    out = []
    n = len(camel)
    for i, ch in enumerate(camel):
        prev = camel[i - 1] if i else ''
        nxt = camel[i + 1] if i + 1 < n else ''
        if i and (
            (ch.isupper() and (prev.islower() or prev.isdigit()))
            or (ch.isupper() and prev.isupper() and nxt.islower())
            or (ch.isdigit() and prev.islower())
        ):
            out.append('_')
        out.append(ch)
    return ''.join(out).lower()
""",
    "rv_split_join": """    parts = re.split(r'(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|(?<=[a-z])(?=[0-9])', camel)
    return '_'.join(parts).lower()
""",
    "rv_acr_min2": """    snake = re.sub(r'([A-Z]{2,})([A-Z][a-z])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
""" + GOLD_RULES_AFTER_ACRONYM,
    # ---- 错误候选：阈值 ----
    "w_acr_max8": """    snake = re.sub(r'(?<![A-Z])([A-Z]{1,8})([A-Z][a-z])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
""" + GOLD_RULES_AFTER_ACRONYM,
    "w_count2": """    snake = re.sub(r'([A-Z]+)([A-Z][a-z])', lambda m: f'{m.group(1)}_{m.group(2)}', camel, count=2)
""" + GOLD_RULES_AFTER_ACRONYM,
    "w_len_cap": """    if len(camel) > 20:
""" + BASE_ALGO + """    snake = re.sub(r'([A-Z]+)([A-Z][a-z])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
""" + GOLD_RULES_AFTER_ACRONYM,
    # ---- 错误候选：位置 ----
    "w_window8": """    snake = re.sub(r'([A-Z]+)(?=[A-Z][a-z])', lambda m: m.group(1) + '_' if m.start() < 8 else m.group(1), camel)
""" + GOLD_RULES_AFTER_ACRONYM,
    "w_mid_underscore": """    core = camel.strip('_')
    lead = camel[: len(camel) - len(camel.lstrip('_'))]
    trail = camel[len(lead) + len(core):]
    core = re.sub(r'(?:^|(?<=[a-z0-9]))([A-Z]+)(?=[A-Z][a-z])', lambda m: m.group(1) + '_', core)
    snake = lead + core + trail
""" + GOLD_RULES_AFTER_ACRONYM,
    "w_last_only": """    matches = list(re.finditer(r'([A-Z]+)(?=[A-Z][a-z])', camel))
    snake = camel
    if matches:
        m = matches[-1]
        snake = camel[: m.end()] + '_' + camel[m.end():]
""" + GOLD_RULES_AFTER_ACRONYM,
    # ---- 错误候选：编码子集 ----
    "w_skip_nonascii": """    if any(ord(ch) > 127 for ch in camel):
""" + BASE_ALGO + """    snake = re.sub(r'([A-Z]+)([A-Z][a-z])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
""" + GOLD_RULES_AFTER_ACRONYM,
    # ---- 退化探测：只特判题面原例 ----
    "w_example_only": """    if camel == 'HTTPResponse':
        return 'http_response'
""" + BASE_BODY,
}


def main() -> None:
    base_path, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    base = base_path.read_text()
    assert base.count(BASE_BODY) == 1, "base to_snake body not found exactly once"
    for name, body in BODIES.items():
        new = base.replace(BASE_BODY, body)
        compile(new, name, "exec")
        diff = difflib.unified_diff(base.splitlines(keepends=True), new.splitlines(keepends=True),
                                    fromfile="a/pydantic/alias_generators.py", tofile="b/pydantic/alias_generators.py")
        text = "diff --git a/pydantic/alias_generators.py b/pydantic/alias_generators.py\n" + "".join(diff)
        (out_dir / f"{name}.patch").write_text(text)
        print(name, len(text))


if __name__ == "__main__":
    main()
