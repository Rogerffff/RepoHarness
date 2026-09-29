"""补查已发生过的结构：完整前置内容块，随后 tool_use 块中途结束。

只在独立实验进程包装作者夹具，不改生产或作者脚本。
使用实际解析器可产生的 text + tool_use；不伪装成旧 DeepSeek 的空 thinking/signature 原样复现。
用原 S0 作完整流正控，原 S3/S5 作 index=1 工具开始后的截断；其余原参数透传。
"""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
import sys
import textwrap


def main() -> int:
    args = sys.argv[1:]
    marker = args.index("--fixture")
    path = Path(args[marker + 1]).resolve()
    del args[marker:marker + 2]
    spec = importlib.util.spec_from_file_location("review_s3_fixture", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    module.TURNS[1]["text"] = "I will run the next diagnostic command.\n" + module.TURNS[1]["text"]
    module.SCENARIOS["S0"]["desc"] = "review: full text block + full tool block; original S0 control"
    module.SCENARIOS["S5"]["desc"] = "review: full text block, then index=1 tool start followed by clean HTTP EOF"
    module.SCENARIOS["S3"]["desc"] = "review: full text block, then index=1 tool start followed by FIN without HTTP terminator"
    for name in ("S3", "S5"):
        module.SCENARIOS[name]["plan"]["target_content_block_index"] = 1
    original = inspect.getsource(module.FaultProxy._pipe_chunked)
    needle = 'ev = m.group(1).decode() if m else "?"'
    assert original.count(needle) == 1
    replacement = needle + '''
            if action and action.get("target_content_block_index") is not None and ev == action.get("after_event"):
                block_index = re.search(rb'"index":\\s*(\\d+)', data)
                if block_index is None or int(block_index.group(1)) != action["target_content_block_index"]:
                    ev += "(earlier-block)"
'''
    namespace = dict(vars(module))
    exec(textwrap.dedent(original.replace(needle, replacement)), namespace)
    module.FaultProxy._pipe_chunked = namespace["_pipe_chunked"]
    return module.main(args)


if __name__ == "__main__":
    raise SystemExit(main())
