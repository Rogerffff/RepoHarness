"""dask__dask-8801 候选生成（私有诊断材料，不交给求解者）。

用法：python make_candidates.py <base config.py> <gold.patch> <输出目录>
从 base 的 dask/config.py 出发：先在内存里套上 gold，再按下表逐个做字符串替换（每处替换都断言恰好命中一次），
输出 <名字>.patch（git apply 可用的统一 diff）与 candidates.json（sha256 与一句话说明）。

候选分三组：
- 合理实现（用于查误拒 T1）：只改措辞、只改路径格式、换异常类型、显式异常链、让 PyYAML 自带文件名；
- 另一种政策（P5 判断用）：警告并跳过坏文件；
- 错误或不完整实现（用于查放过 T2/T3）：只拒部分类型、空文件也报错、权限错误也报错、报错指向错误文件、
  静默跳过、不包装语法错误、报错不给原因。
"""

import difflib
import hashlib
import json
import sys
from pathlib import Path

base_path, gold_patch_path, out_dir = map(Path, sys.argv[1:4])
out_dir.mkdir(parents=True, exist_ok=True)
BASE = base_path.read_text()

# ---- 在内存里套 gold（gold 只改 dask/config.py 两处 hunk） ----
OLD_LOOP = """    for path in file_paths:
        try:
            with open(path) as f:
                data = yaml.safe_load(f.read()) or {}
                configs.append(data)
        except OSError:
            # Ignore permission errors
            pass
"""
GOLD_LOOP = """    for path in file_paths:
        config = _load_config_file(path)
        if config is not None:
            configs.append(config)
"""
GOLD_HELPER = '''def _load_config_file(path: str) -> dict | None:
    """A helper for loading a config file from a path, and erroring
    appropriately if the file is malformed."""
    try:
        with open(path) as f:
            config = yaml.safe_load(f.read())
    except OSError:
        # Ignore permission errors
        return None
    except Exception as exc:
        raise ValueError(
            f"A dask config file at {path!r} is malformed, original error "
            f"message:\\n\\n{exc}"
        ) from None
    if config is not None and not isinstance(config, dict):
        raise ValueError(
            f"A dask config file at {path!r} is malformed - config files must have "
            f"a dict as the top level object, got a {type(config).__name__} instead"
        )
    return config


def collect_yaml('''


def sub(text: str, old: str, new: str, count: int = 1) -> str:
    assert text.count(old) == count, (old[:80], text.count(old))
    return text.replace(old, new)


GOLD = sub(BASE, "def collect_yaml(", GOLD_HELPER)
GOLD = sub(GOLD, OLD_LOOP, GOLD_LOOP)

PARSE_MSG = '''            f"A dask config file at {path!r} is malformed, original error "
            f"message:\\n\\n{exc}"'''
TYPE_MSG = '''            f"A dask config file at {path!r} is malformed - config files must have "
            f"a dict as the top level object, got a {type(config).__name__} instead"'''
SYN_PARSE = '''            f"Invalid Dask configuration at {path!r}: {exc}"'''
SYN_TYPE = '''            f"Invalid Dask configuration at {path!r}: expected a mapping at the "
            f"document root, got {type(config).__name__}"'''
PRED = "    if config is not None and not isinstance(config, dict):\n"
PARSE_BLOCK = '''    except Exception as exc:
        raise ValueError(
            f"A dask config file at {path!r} is malformed, original error "
            f"message:\\n\\n{exc}"
        ) from None
'''
TYPE_RAISE = '''        raise ValueError(
            f"A dask config file at {path!r} is malformed - config files must have "'''
TYPE_RAISE_FULL = '''        raise ValueError(
            f"A dask config file at {path!r} is malformed - config files must have "
            f"a dict as the top level object, got a {type(config).__name__} instead"
        )'''
OSERR_BLOCK = """    except OSError:
        # Ignore permission errors
        return None
"""

variants: dict[str, tuple[str, str]] = {}

# ---- 合理实现 ----
v = sub(sub(GOLD, PARSE_MSG, SYN_PARSE), TYPE_MSG, SYN_TYPE)
variants["syn_repr"] = (v, "只改措辞：保留 ValueError、{path!r}、解析器原文与类型名，去掉三个英文词组")
variants["gold_plain"] = (sub(GOLD, "{path!r}", "{path}", count=2), "gold 措辞不变，只把 {path!r} 改成 {path}（路径不带引号）")
variants["syn_plain"] = (sub(v, "{path!r}", "{path}", count=2), "措辞与路径格式都改（2x2 因子设计的第四格）")
variants["typeerror"] = (
    sub(GOLD, TYPE_RAISE, TYPE_RAISE.replace("raise ValueError(", "raise TypeError(")),
    "gold 措辞与 {path!r} 不变；顶层非映射改抛 TypeError，语法错误仍抛 ValueError",
)
variants["chain_cause"] = (
    sub(
        sub(
            GOLD,
            PARSE_BLOCK,
            '''    except Exception as exc:
        raise ValueError(f"Could not parse the Dask config file {path!r}") from exc
''',
        ),
        TYPE_MSG,
        '''            f"The Dask config file {path!r} must contain a mapping at the top "
            f"level, not a {type(config).__name__}"''',
    ),
    "语法错误用 raise ... from exc 显式链接解析器原异常（原因在 __cause__ 中显示）；类型错误换措辞",
)
variants["stream_load"] = (
    sub(sub(GOLD, "yaml.safe_load(f.read())", "yaml.safe_load(f)"), PARSE_BLOCK, ""),
    "语法错误不包装：改为 yaml.safe_load(f)，让 PyYAML 的原异常自带文件名与行列；类型检查同 gold",
)

# ---- 另一种政策 ----
variants["warn_skip"] = (
    sub(
        sub(
            GOLD,
            PARSE_BLOCK,
            '''    except Exception as exc:
        warnings.warn(f"Skipping malformed Dask config file {path!r}: {exc}")
        return None
''',
        ),
        TYPE_RAISE_FULL,
        '''        warnings.warn(
            f"Skipping Dask config file {path!r}: the top level must be a mapping, "
            f"got a {type(config).__name__}"
        )
        return None''',
    ),
    "警告并跳过坏文件（警告含路径与原因），其余配置照常加载、import 成功",
)

# ---- 错误或不完整实现 ----
variants["silent_skip"] = (
    sub(
        sub(GOLD, PARSE_BLOCK, "    except Exception:\n        return None\n"),
        TYPE_RAISE_FULL,
        "        return None",
    ),
    "吞掉错误：坏文件一律静默跳过，没有任何诊断",
)
variants["lists_only"] = (sub(GOLD, PRED, "    if isinstance(config, list):\n"), "只拒 list：题面原例的顶层 str 仍进入 merge")
variants["str_only"] = (sub(GOLD, PRED, "    if isinstance(config, str):\n"), "只拒 str（只处理题面原例的类型）")
variants["list_str_only"] = (
    sub(GOLD, PRED, "    if isinstance(config, (list, str)):\n"),
    "只拒 list 与 str：顶层数字等其它标量仍进入 merge",
)
variants["none_raises"] = (
    sub(GOLD, PRED, "    if not isinstance(config, dict):\n"),
    "去掉 None 例外：空文件与全注释文件（ensure_file(comment=True) 的产物）也报错",
)
variants["oserr_fatal"] = (sub(GOLD, OSERR_BLOCK, ""), "去掉 OSError 例外：不可读文件也被包装成 ValueError")
variants["typeonly"] = (sub(GOLD, PARSE_BLOCK, ""), "只加顶层类型检查（gold 措辞），不包装 YAML 语法错误")
variants["noreason"] = (
    sub(
        sub(
            GOLD,
            PARSE_BLOCK,
            '''    except Exception:
        raise ValueError(f"Invalid Dask config file {path!r}") from None
''',
        ),
        TYPE_MSG,
        '''            f"Invalid Dask config file {path!r}"''',
    ),
    "报错只给路径不给原因：语法错误用 from None 隐去解析器信息，类型错误不说期望什么、得到什么",
)
variants["parsererror_only"] = (
    sub(GOLD, "    except Exception as exc:\n", "    except yaml.parser.ParserError as exc:\n"),
    "只包装 yaml.parser.ParserError：制表符缩进、'a: b: c' 等 ScannerError 仍以原异常抛出、不含文件名",
)
variants["import_swallow"] = (
    sub(
        GOLD,
        "\n\nrefresh()\n_initialize()\n",
        '''

try:
    refresh()
except ValueError as exc:
    warnings.warn(f"Ignoring Dask configuration files: {exc}")
_initialize()
''',
    ),
    "collect_yaml 同 gold 抛错，但模块导入时的 refresh() 捕获并警告：import dask 照常成功，用户配置全部丢弃",
)
# ---- 独立复核提出的候选（review.md 附录），按其文字描述重建，不是复核者补丁的逐字节副本 ----
GOLD_HELPER_BODY_START = '''def _load_config_file(path: str) -> dict | None:'''
KV_HELPER = '''class ConfigFileError(ValueError):
    """Raised when a Dask config file cannot be used as configuration."""


def _load_config_file(path: str) -> dict | None:
    """Load one config file; unreadable files are skipped."""
    try:
        with open(path) as f:
            config = yaml.safe_load(f.read())
    except OSError:
        return None
    except yaml.YAMLError as exc:
        raise ConfigFileError(f"Could not parse Dask config file {path}") from exc
    if config is not None and not isinstance(config, Mapping):
        raise ConfigFileError(
            f"Dask config file {path} must contain key: value pairs at the top level, "
            f"found {config!r}"
        )
    return config
'''
_gold_helper_block = GOLD_HELPER[: GOLD_HELPER.index("\n\ndef collect_yaml(")] + "\n"
variants["rv_kv_pairs"] = (
    sub(GOLD, _gold_helper_block, KV_HELPER),
    "复核者的合理实现：自定义 ConfigFileError(ValueError)，消息说 'must contain key: value pairs' 并给出实际内容，"
    "语法错误用 from exc 保留原因（按 review.md 附录重建）",
)
DIR_ONLY_LIST = """                try:
                    file_paths.extend(
                        sorted(
                            os.path.join(path, p)
                            for p in os.listdir(path)
                            if os.path.splitext(p)[1].lower()
                            in (".json", ".yaml", ".yml")
                        )
                    )
"""
DIR_ONLY_LIST_NEW = """                try:
                    found = sorted(
                        os.path.join(path, p)
                        for p in os.listdir(path)
                        if os.path.splitext(p)[1].lower() in (".json", ".yaml", ".yml")
                    )
                    file_paths.extend(found)
                    from_dirs.update(found)
"""
v = sub(GOLD, DIR_ONLY_LIST, DIR_ONLY_LIST_NEW)
v = sub(v, "    # Find all paths\n    file_paths = []\n", "    # Find all paths\n    file_paths = []\n    from_dirs = builtins.set()  # dask.config shadows set\n")
v = sub(
    v,
    GOLD_LOOP,
    """    for path in file_paths:
        if path in from_dirs:
            config = _load_config_file(path)
            if config is not None:
                configs.append(config)
        else:
            try:
                with open(path) as f:
                    data = yaml.safe_load(f.read()) or {}
                    configs.append(data)
            except OSError:
                # Ignore permission errors
                pass
""",
)
variants["rv_dir_only"] = (
    v,
    "复核者的错误候选：gold 的校验只用于目录里枚举到的文件，直接给出的文件路径仍走 base 的 `safe_load(...) or {}`（按附录重建）",
)
v = sub(GOLD, "def collect_yaml(paths: Sequence[str] = paths) -> list[dict]:", 'def collect_yaml(paths: Sequence[str] = paths, on_error: str = "raise") -> list[dict]:')
v = sub(
    v,
    GOLD_LOOP,
    """    for path in file_paths:
        try:
            config = _load_config_file(path)
        except ValueError as exc:
            if on_error != "warn":
                raise
            warnings.warn(f"{exc}\\n\\nThis file is ignored.")
            continue
        if config is not None:
            configs.append(config)
""",
)
v = sub(
    v,
    "def collect(paths: list[str] = paths, env: Mapping[str, str] = None) -> dict:",
    'def collect(\n    paths: list[str] = paths, env: Mapping[str, str] = None, on_error: str = "raise"\n) -> dict:',
)
v = sub(v, "    configs = collect_yaml(paths=paths)\n", "    configs = collect_yaml(paths=paths, on_error=on_error)\n")
v = sub(v, "\n\nrefresh()\n_initialize()\n", '\n\nrefresh(on_error="warn")\n_initialize()\n')
variants["rv_import_warn"] = (
    v,
    "复核者的另一政策候选：API（collect_yaml/collect/refresh）默认抛错；模块导入时 on_error='warn'，"
    "对坏文件发出点名文件的警告并只跳过该文件（按附录重建）",
)
variants["rv_enum_types"] = (
    sub(GOLD, PRED, "    if isinstance(config, (list, str, int)):\n"),
    "复核者的错误候选：只拒 list、str、int，顶层 float／日期仍进入 merge（已登记 T3，只做私有对照）",
)
WRONG_FILE_LOOP = """    for path in file_paths:
        try:
            with open(path) as f:
                data = yaml.safe_load(f.read()) or {}
                configs.append(data)
        except OSError:
            # Ignore permission errors
            pass
        except Exception as exc:
            raise ValueError(
                f"A dask config file at {path!r} is malformed, original error "
                f"message:\\n\\n{exc}"
            ) from None

    for config in configs:
        if not isinstance(config, dict):
            raise ValueError(
                f"A dask config file at {path!r} is malformed - config files must have "
                f"a dict as the top level object, got a {type(config).__name__} instead"
            )
"""
variants["wrong_file"] = (
    sub(BASE, OLD_LOOP, WRONG_FILE_LOOP),
    "读完所有文件后再检查类型，报错用循环变量 path（即最后一个文件），坏文件不是最后一个时指错文件",
)


def to_patch(new: str) -> str:
    lines = difflib.unified_diff(
        BASE.splitlines(keepends=True), new.splitlines(keepends=True), "a/dask/config.py", "b/dask/config.py", n=3
    )
    return "diff --git a/dask/config.py b/dask/config.py\n" + "".join(lines)


meta = {}
for name, (text, why) in variants.items():
    compile(text, name, "exec")
    patch = to_patch(text)
    (out_dir / f"{name}.patch").write_text(patch)
    meta[name] = {"sha256": hashlib.sha256(patch.encode()).hexdigest(), "what": why}
# gold 自检：内存套用结果与官方 gold 补丁作用后应一致（由 behavior 对照中 git apply 的结果另行核对）
meta["_gold_inmemory_sha256"] = hashlib.sha256(GOLD.encode()).hexdigest()
(out_dir / "candidates.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n")
print(json.dumps({k: v if k.startswith("_") else v["sha256"][:12] for k, v in meta.items()}, indent=1))
