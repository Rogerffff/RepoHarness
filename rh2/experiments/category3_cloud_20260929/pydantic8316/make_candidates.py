"""pydantic-8316 候选构造：每个候选只替换 base `pydantic/alias_generators.py` 中 `to_snake` 的函数体（docstring 之后），
输出 <name>.patch（git 风格，a/ b/ 前缀），供私有矩阵与正式评分使用。
用法：python make_candidates.py <base_alias_generators.py> <out_dir>
候选分组（按公开要求判对错，不以 gold 为答案）：
  合理替代实现（查误拒 T1）：keep_digit、lookaround、scan、upstream_main；第二组 normalize
  错误候选（查漏判）：lead_only、first_only、acr3、literal；第二组 lower_or_start、no_lower_upper、acr_max4、only_if_no_us
  第三组（09-30 主审补充）：skip_if_underscore、skip_if_digit、lower_or_start_la、acr_max5、no_trailing_upper（查 v1 是否放过），
    no_digit_split、no_digit_upper（查 P2P 保护了哪些数字边界）
"""
import difflib
import sys
from pathlib import Path

BASE_BODY = """    snake = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
    snake = re.sub(r'([a-z0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    return snake.lower()
"""

BODIES = {
    # 合理替代 1：在 base 两条规则之前加“缩写接首字母大写单词”的分隔，完整保留 base 的字母→数字规则（A1 -> a_1）
    "keep_digit": """    # split an acronym from a following capitalized word: HTTPResponse -> HTTP_Response
    snake = re.sub(r'([A-Z]+)([A-Z][a-z])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
    snake = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    snake = re.sub(r'([a-z0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    return snake.lower()
""",
    # 合理替代 2：上游 2.8.0（#9747）的单条环视正则，去掉该版本另加的 kebab `-` 分支；同样保留 base 的字母→数字规则
    "lookaround": """    snake = re.sub(r'(?<=[a-zA-Z])(?=[0-9])|(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', '_', camel)
    return snake.lower()
""",
    # 合理替代 3：逐字符扫描（不用正则），保留 base 的字母→数字规则；用 str.isupper 等，Unicode 行为与正则写法不同（题面未要求）
    "scan": """    out = []
    n = len(camel)
    for i, ch in enumerate(camel):
        prev = camel[i - 1] if i > 0 else ''
        nxt = camel[i + 1] if i + 1 < n else ''
        if i > 0 and (
            (ch.isupper() and (prev.islower() or prev.isdigit()))
            or (ch.isupper() and prev.isupper() and nxt.islower())
            or (ch.isdigit() and prev.isalpha())
        ):
            out.append('_')
        out.append(ch)
    return ''.join(out).lower()
""",
    # 上游式：上游 2.9.0 至 main 的写法（gold 四条正则 + kebab `-` 替换）
    "upstream_main": """    # Handle the sequence of uppercase letters followed by a lowercase letter
    snake = re.sub(r'([A-Z]+)([A-Z][a-z])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
    # Insert an underscore between a lowercase letter and an uppercase letter
    snake = re.sub(r'([a-z])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    # Insert an underscore between a digit and an uppercase letter
    snake = re.sub(r'([0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    # Insert an underscore between a lowercase letter and a digit
    snake = re.sub(r'([a-z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    # Replace hyphens with underscores to handle kebab-case
    snake = snake.replace('-', '_')
    return snake.lower()
""",
    # 错误 1（只处理题面示例的输入形态）：只拆开头的缩写（允许前导下划线），中间的缩写不处理
    "lead_only": """    # split a leading acronym from the following word: HTTPResponse -> HTTP_Response
    snake = re.sub(r'^(_*[A-Z]+)([A-Z][a-z])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
    snake = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    snake = re.sub(r'([a-z0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    return snake.lower()
""",
    # 错误 2（依赖出现次序）：缩写规则只替换第一处（count=1），后面的缩写不处理
    "first_only": """    # split the acronym from the following word: HTTPResponse -> HTTP_Response
    snake = re.sub(r'([A-Z]+)([A-Z][a-z])', lambda m: f'{m.group(1)}_{m.group(2)}', camel, count=1)
    snake = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    snake = re.sub(r'([a-z0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    return snake.lower()
""",
    # 错误 3（阈值）：只把 3 个及以上大写字母的连续段当缩写（HTTP、CAMEL 可以，ID、IO、IP 这类两字母缩写不行）
    "acr3": """    # split an acronym (3+ capitals) from the following word: HTTPResponse -> HTTP_Response
    snake = re.sub(r'([A-Z]{3,})([A-Z][a-z])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
    snake = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    snake = re.sub(r'([a-z0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    return snake.lower()
""",
    # 错误 4（只处理题面示例字面值／固定子集）：只认一张常见缩写表
    "literal": """    for acronym in ('HTTP', 'HTTPS', 'URL', 'API', 'JSON', 'XML', 'ID'):
        camel = re.sub(f'({acronym})([A-Z][a-z])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
    snake = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
    snake = re.sub(r'([a-z0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    return snake.lower()
""",
    # ---- 第二组（修订草案压力测试，私有矩阵用）----
    # 合理替代 5：先把“后接单词的缩写”规范成首字母大写（HTTPResponse -> HttpResponse），再走 base 两条规则
    "normalize": """    # normalize an acronym that is followed by a capitalized word: HTTPResponse -> HttpResponse
    camel = re.sub(r'([A-Z])([A-Z]+)(?=[A-Z][a-z])', lambda m: m.group(1) + m.group(2).lower(), camel)
    snake = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
    snake = re.sub(r'([a-z0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    return snake.lower()
""",
    # 错误 5（位置子集）：缩写只在串首或小写字母之后才拆（下划线、数字之后的缩写不拆）
    "lower_or_start": """    snake = re.sub(r'(^|[a-z])([A-Z]+)([A-Z][a-z])', lambda m: f'{m.group(1)}{m.group(2)}_{m.group(3)}', camel)
    snake = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    snake = re.sub(r'([a-z0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    return snake.lower()
""",
    # 错误 6（丢掉旧规则）：只在“大写字母后接小写字母”之前断开，删掉 base 的“小写/数字→大写”规则
    "no_lower_upper": """    snake = re.sub(r'(?<=[A-Za-z0-9])(?=[A-Z][a-z])', '_', camel)
    snake = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    return snake.lower()
""",
    # 错误 7（上限阈值）：只认 2–4 个字母的缩写（HTTP 可以，CAMEL 这类 5 个字母的不行）
    "acr_max4": """    snake = re.sub(r'(?<![A-Z])([A-Z]{2,4})([A-Z][a-z])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
    snake = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    snake = re.sub(r'([a-z0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    return snake.lower()
""",
    # 错误 8（只在症状出现时修）：旧结果里完全没有下划线时才改用缩写规则
    "only_if_no_us": """    snake = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
    snake = re.sub(r'([a-z0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    if '_' not in snake.strip('_'):
        snake = re.sub(r'([A-Z]+)([A-Z][a-z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    return snake.lower()
""",
    # ---- 第三组（09-30 主审补充：v1 可能放过的构造、数字边界的保护范围）----
    # 错误 9（数据形态子集）：输入里已有下划线就当作 snake_case，沿用 base 两条规则，不做缩写拆分（_HTTPResponse 不修）
    "skip_if_underscore": """    if '_' in camel:
        # already (partly) snake_case: keep the old conversion
        snake = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
        snake = re.sub(r'([a-z0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
        return snake.lower()
    snake = re.sub(r'([A-Z]+)([A-Z][a-z])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
    snake = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    snake = re.sub(r'([a-z0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    return snake.lower()
""",
    # 错误 10（位置子集，零宽写法）：缩写只在串首或小写字母之后才拆；与 lower_or_start 不同，不吞掉前一个字符，
    # 所以连续两个缩写（XMLToJSON）也能拆，只有下划线、数字之后的缩写不拆
    "lower_or_start_la": """    snake = re.sub(r'(?:^|(?<=[a-z]))([A-Z]+)(?=[A-Z][a-z])', lambda m: f'{m.group(1)}_', camel)
    snake = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    snake = re.sub(r'([a-z0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    return snake.lower()
""",
    # 错误 11（上限阈值，放宽到 5）：只认 1–5 个字母的缩写（CAMEL 可以，6 个及以上字母的不行）
    "acr_max5": """    snake = re.sub(r'(?<![A-Z])([A-Z]{1,5})([A-Z][a-z])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
    snake = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    snake = re.sub(r'([a-z0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    return snake.lower()
""",
    # 错误 12（整条改写成“只在单词开头的大写字母前断开”）：在“小写/数字 → 大写开头的单词或缩写”之前、
    # “缩写 → 大写开头的单词”之前断开；丢掉 base 对末尾缩写和单个大写字母的拆分（userID -> userid、parseURL -> parseurl）
    "no_trailing_upper": """    snake = re.sub(r'(?<=[a-z0-9])(?=[A-Z]+[a-z])|(?<=[A-Z])(?=[A-Z][a-z])', '_', camel)
    snake = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    return snake.lower()
""",
    # 错误 9b（数据形态子集，同 skip_if_underscore 的“对旧测试覆盖的形态保留旧行为”）：含数字的输入沿用 base 两条规则
    "skip_if_digit": """    if any(ch.isdigit() for ch in camel):
        # keep the old conversion for inputs with digits
        snake = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
        snake = re.sub(r'([a-z0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
        return snake.lower()
    snake = re.sub(r'([A-Z]+)([A-Z][a-z])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
    snake = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    snake = re.sub(r'([a-z0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    return snake.lower()
""",
    # 错误 13（丢掉旧的字母→数字规则）：修了缩写，但字母与数字之间都不再断开（camel2 -> camel2）
    "no_digit_split": """    snake = re.sub(r'([A-Z]+)([A-Z][a-z])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
    snake = re.sub(r'([a-z0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    return snake.lower()
""",
    # 错误 14（丢掉旧的数字→大写规则）：修了缩写，但数字与大写字母之间不再断开（Camel2Snake -> camel_2snake）
    "no_digit_upper": """    snake = re.sub(r'([A-Z]+)([A-Z][a-z])', lambda m: f'{m.group(1)}_{m.group(2)}', camel)
    snake = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    snake = re.sub(r'([a-z])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', snake)
    return snake.lower()
""",
}


def main() -> None:
    base_path, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    base = base_path.read_text()
    assert base.count(BASE_BODY) == 1, "base to_snake body not found exactly once"
    for name, body in BODIES.items():
        new = base.replace(BASE_BODY, body)
        diff = difflib.unified_diff(base.splitlines(keepends=True), new.splitlines(keepends=True),
                                    fromfile="a/pydantic/alias_generators.py", tofile="b/pydantic/alias_generators.py")
        text = "diff --git a/pydantic/alias_generators.py b/pydantic/alias_generators.py\n" + "".join(diff)
        (out_dir / f"{name}.patch").write_text(text)
        print(name, len(text))


if __name__ == "__main__":
    main()
