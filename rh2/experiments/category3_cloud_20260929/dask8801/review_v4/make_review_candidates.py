"""dask__dask-8801 v4 聚焦复核：复核者自造候选（私有诊断材料，不交给求解者）。

用法：python make_review_candidates.py <base config.py> <输出目录>
从 base 的 dask/config.py 出发，逐个做字符串替换（每处替换都断言恰好命中一次），
输出 <名字>.patch（git apply 可用的统一 diff）与 candidates_review.json（sha256 与一句话说明）。

三组：
- ok_*：措辞、异常类型或结构与 gold 不同、但按公开要求应当合格的实现（查 v4 的新误拒）；
- gr_*：灰区探针（判断见 review_v4.md）；
- wr_*：针对 v4 放宽处（任意异常类型、不要求引号、词表、目录形态）另造的错误实现（查放过）。
"""

import difflib
import hashlib
import json
import sys
from pathlib import Path

base_path, out_dir = map(Path, sys.argv[1:3])
out_dir.mkdir(parents=True, exist_ok=True)
BASE = base_path.read_text()


def sub(text: str, old: str, new: str, count: int = 1) -> str:
    assert text.count(old) == count, (old[:80], text.count(old))
    return text.replace(old, new)


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
GOLD = sub(sub(BASE, "def collect_yaml(", GOLD_HELPER), OLD_LOOP, GOLD_LOOP)
CY = "def collect_yaml("
variants: dict[str, tuple[str, str]] = {}

# ======================= ok_*：应当合格 =======================
variants["ok_object_value"] = (
    sub(
        sub(
            BASE,
            CY,
            '''class ConfigFileError(Exception):
    """A Dask configuration file exists but cannot be used as configuration."""


def _read_config_file(path: str):
    try:
        with open(path) as f:
            text = f.read()
    except OSError:
        # Ignore permission errors
        return None
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigFileError(f"Could not parse Dask config file {path}") from exc
    if data is not None and not isinstance(data, Mapping):
        raise ConfigFileError(
            f"Dask config file {path} must contain an object at the top level, "
            f"found {data!r}"
        )
    return data


def collect_yaml(''',
        ),
        OLD_LOOP,
        """    for path in file_paths:
        data = _read_config_file(path)
        if data is not None:
            configs.append(data)
""",
    ),
    "自定义 ConfigFileError(Exception)（非 ValueError）；语法错误 from exc；非映射说 'must contain an object at the top level, "
    "found <值的 repr>'，不写类型名、dict、mapping、key",
)
variants["ok_map_settings"] = (
    sub(
        BASE,
        OLD_LOOP,
        """    for path in file_paths:
        try:
            with open(path) as f:
                text = f.read()
        except OSError:
            # Ignore permission errors
            continue
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError:
            raise ValueError(f"Invalid YAML in Dask config file {path}")
        if data is None:
            # Empty or fully commented-out file
            continue
        if not isinstance(data, Mapping):
            raise TypeError(
                f"The Dask config file {path} should be a YAML map of settings, "
                f"but its top level is {data!r}"
            )
        configs.append(data)
""",
    ),
    "校验直接写在 collect_yaml 循环里；语法错误在 except 块内重新抛出（隐式异常链显示原因）；非映射抛 TypeError，"
    "说 'should be a YAML map of settings, but its top level is <值的 repr>'",
)
variants["ok_dictionary_typeerror"] = (
    sub(
        BASE,
        OLD_LOOP,
        """    for path in file_paths:
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
        except OSError:
            # Ignore permission errors
            continue
        except yaml.YAMLError as exc:
            raise ValueError(f"{path}: {exc}") from exc
        if data is None:
            continue
        if not isinstance(data, dict):
            raise TypeError(
                f"{path}: the top level must be a dictionary, not {type(data).__name__}"
            )
        configs.append(data)
""",
    ),
    "循环内校验、流式加载；语法错误 ValueError(path: 原消息) from exc；非映射 TypeError 'must be a dictionary, not <类型>'",
)
variants["ok_aggregate"] = (
    sub(
        BASE,
        OLD_LOOP,
        """    errors = []
    for path in file_paths:
        try:
            with open(path) as f:
                data = yaml.safe_load(f.read())
        except OSError:
            # Ignore permission errors
            continue
        except yaml.YAMLError as exc:
            errors.append(f"{path}: invalid YAML: {exc}")
            continue
        if data is None:
            continue
        if not isinstance(data, Mapping):
            errors.append(
                f"{path}: top-level YAML must be a mapping, got {type(data).__name__}"
            )
            continue
        configs.append(data)

    if errors:
        raise ValueError(
            "Invalid Dask configuration file(s):\\n" + "\\n".join("  " + e for e in errors)
        )
""",
    ),
    "先检查全部文件，再一次性抛出一个列出每个坏文件及原因的 ValueError（结构不同）",
)
variants["ok_yamlerror_subclass"] = (
    sub(
        sub(
            sub(BASE, "import threading\n", "import pathlib\nimport threading\n"),
            CY,
            '''class DaskConfigError(yaml.YAMLError):
    """Raised when a Dask configuration file cannot be used."""


def _load_yaml_config(path: str) -> dict | None:
    try:
        text = pathlib.Path(path).read_text()
    except OSError:
        # Ignore permission errors
        return None
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise DaskConfigError(f"Error in Dask config file {path}:\\n{exc}") from exc
    if data is not None and not isinstance(data, Mapping):
        raise DaskConfigError(
            f"Dask config file {path} must contain key/value pairs at the top level, "
            f"got {type(data).__name__}"
        )
    return data


def collect_yaml(''',
        ),
        OLD_LOOP,
        """    for path in file_paths:
        data = _load_yaml_config(path)
        if data is not None:
            configs.append(data)
""",
    ),
    "异常类是 yaml.YAMLError 的子类（与 base 语法错误同一基类）；pathlib 读取；消息 'must contain key/value pairs ... got <类型>'",
)
variants["ok_falsy_empty"] = (
    sub(
        BASE,
        OLD_LOOP,
        """    for path in file_paths:
        try:
            with open(path) as f:
                data = yaml.safe_load(f.read()) or {}
        except OSError:
            # Ignore permission errors
            continue
        except yaml.YAMLError as exc:
            raise ValueError(f"Could not parse Dask config file {path!r}") from exc
        if not isinstance(data, dict):
            raise ValueError(
                f"Dask config file {path!r} must contain a mapping at the top level, "
                f"got {type(data).__name__}"
            )
        configs.append(data)
""",
    ),
    "保留 base 的 `or {}`：顶层假值（[]、''、0、false）照旧当空配置（T3，与 base 一致）；其余同 gold 语义",
)

# ======================= gr_*：灰区探针 =======================
variants["gr_attr_wrap"] = (
    sub(
        BASE,
        OLD_LOOP,
        """    for path in file_paths:
        try:
            with open(path) as f:
                data = yaml.safe_load(f.read()) or {}
            update({}, data)  # make sure the file can be merged
        except OSError:
            # Ignore permission errors
            continue
        except Exception as exc:
            raise ValueError(f"Could not load Dask config file {path}: {exc}") from exc
        configs.append(data)
""",
    ),
    "不写类型检查，只用 update({}, data) 试合并；任何异常包装成 'Could not load Dask config file <路径>: <原异常>'，"
    "非映射时原因文字就是原来的 \"'str' object has no attribute 'items'\"",
)
variants["gr_basename_only"] = (
    sub(GOLD, "{path!r}", "{os.path.basename(path)!r}", count=2),
    "gold 只把消息里的完整路径换成文件名（不含目录）",
)
variants["gr_csafe_loader"] = (
    sub(GOLD, "config = yaml.safe_load(f.read())", "config = yaml.load(f.read(), Loader=yaml.CSafeLoader)"),
    "gold 只把解析器换成 libyaml 的 CSafeLoader（原因文字随之变成 libyaml 的措辞）",
)

# ======================= wr_*：错误或不完整 =======================
ZIP_TAIL = """
    for path, config in zip(file_paths, configs):
        if not isinstance(config, dict):
            raise ValueError(
                f"A dask config file at {path!r} is malformed - config files must have "
                f"a dict as the top level object, got a {type(config).__name__} instead"
            )
"""
variants["wr_zip_misalign"] = (
    sub(
        BASE,
        OLD_LOOP,
        """    for path in file_paths:
        try:
            with open(path) as f:
                data = yaml.safe_load(f.read())
        except OSError:
            # Ignore permission errors
            continue
        except yaml.YAMLError as exc:
            raise ValueError(
                f"A dask config file at {path!r} is malformed, original error "
                f"message:\\n\\n{exc}"
            ) from None
        if data is not None:
            configs.append(data)
"""
        + ZIP_TAIL,
    ),
    "读完再用 zip(file_paths, configs) 检查类型；空文件、全注释文件（None）与不可读条目被跳过后两表错位，"
    "坏文件前面只要有这样的条目，报错就点名前面的另一个文件",
)
variants["wr_zip_misalign_orempty"] = (
    sub(
        BASE,
        OLD_LOOP,
        """    for path in file_paths:
        try:
            with open(path) as f:
                data = yaml.safe_load(f.read()) or {}
        except OSError:
            # Ignore permission errors
            continue
        except yaml.YAMLError as exc:
            raise ValueError(
                f"A dask config file at {path!r} is malformed, original error "
                f"message:\\n\\n{exc}"
            ) from None
        configs.append(data)
"""
        + ZIP_TAIL,
    ),
    "同上但保留 `or {}`：只有不可读条目会让两表错位（坏文件前有不可读条目时点名错误文件）",
)
variants["wr_all_files"] = (
    sub(
        BASE,
        OLD_LOOP,
        """    try:
        for path in file_paths:
            try:
                with open(path) as f:
                    data = yaml.safe_load(f.read())
            except OSError:
                # Ignore permission errors
                continue
            if data is None:
                continue
            if not isinstance(data, dict):
                raise TypeError(
                    f"config files must have a dict as the top level object, "
                    f"got a {type(data).__name__}"
                )
            configs.append(data)
    except (yaml.YAMLError, TypeError) as exc:
        raise ValueError(
            f"Could not load Dask configuration from {file_paths}: {exc}"
        ) from exc
""",
    ),
    "整个循环外包一层，报错列出所有找到的配置文件（不指出哪一个坏）",
)
variants["wr_dir_named"] = (
    sub(
        BASE,
        OLD_LOOP,
        """    for path in file_paths:
        try:
            with open(path) as f:
                data = yaml.safe_load(f.read())
        except OSError:
            # Ignore permission errors
            continue
        except yaml.YAMLError as exc:
            raise ValueError(f"Malformed Dask config in {paths}: {exc}") from exc
        if data is None:
            continue
        if not isinstance(data, dict):
            raise ValueError(
                f"Malformed Dask config in {paths}: top level must be a mapping, "
                f"got {type(data).__name__}"
            )
        configs.append(data)
""",
    ),
    "报错只点名搜索路径（目录），不点名目录里的坏文件",
)
variants["wr_import_only"] = (
    sub(
        sub(
            BASE,
            OLD_LOOP,
            """    for path in file_paths:
        try:
            with open(path) as f:
                data = yaml.safe_load(f.read())
        except (OSError, yaml.YAMLError):
            continue
        if isinstance(data, dict):
            configs.append(data)
""",
        ),
        "\n\nrefresh()\n_initialize()\n",
        '''

def _check_config_files(paths: Sequence[str] = paths) -> None:
    """Fail early at import time if a config file cannot be used."""
    for search_path in paths:
        if os.path.isdir(search_path):
            try:
                names = sorted(os.listdir(search_path))
            except OSError:
                continue
            files = [
                os.path.join(search_path, n)
                for n in names
                if os.path.splitext(n)[1].lower() in (".json", ".yaml", ".yml")
            ]
        elif os.path.exists(search_path):
            files = [search_path]
        else:
            continue
        for fn in files:
            try:
                with open(fn) as f:
                    data = yaml.safe_load(f.read())
            except OSError:
                continue
            except yaml.YAMLError as exc:
                raise ValueError(f"Could not parse Dask config file {fn}: {exc}") from exc
            if data is not None and not isinstance(data, dict):
                raise ValueError(
                    f"Dask config file {fn} must contain a mapping at the top level, "
                    f"got {type(data).__name__}"
                )


_check_config_files()
refresh()
_initialize()
''',
    ),
    "只在导入路径报错：collect_yaml/collect/refresh 静默跳过坏文件，模块导入时另做一遍检查并抛错",
)
variants["wr_wrong_reason"] = (
    sub(
        BASE,
        OLD_LOOP,
        """    for path in file_paths:
        try:
            with open(path) as f:
                data = yaml.safe_load(f.read())
        except OSError:
            # Ignore permission errors
            continue
        except yaml.YAMLError as exc:
            raise ValueError(f"Dask config file {path} is not valid YAML") from exc
        if data is None:
            continue
        if not isinstance(data, dict):
            raise ValueError(f"Dask config file {path} is not valid YAML")
        configs.append(data)
""",
    ),
    "报错原因写错：顶层非映射（YAML 本身合法）也说 'is not valid YAML'",
)
variants["wr_perm_fatal"] = (
    sub(
        GOLD,
        """    except OSError:
        # Ignore permission errors
        return None
""",
        """    except PermissionError as exc:
        raise ValueError(f"Cannot read Dask config file {path!r}: {exc}") from exc
    except OSError:
        # Not a readable file (e.g. a directory, or removed meanwhile)
        return None
""",
    ),
    "gold 上把权限错误改成致命错误，其它 OSError（目录、文件已删除）仍跳过：违反公开权限测试，c.yaml 检查拦不住",
)
variants["wr_open_unguarded"] = (
    sub(
        BASE,
        OLD_LOOP,
        """    for path in file_paths:
        with open(path) as f:
            text = f.read()
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ValueError(f"Could not parse Dask config file {path}: {exc}") from exc
        if data is None:
            continue
        if not isinstance(data, dict):
            raise ValueError(
                f"Dask config file {path} must contain a mapping at the top level, "
                f"got {type(data).__name__}"
            )
        configs.append(data)
""",
    ),
    "oserr_fatal 的另一种自然写法：重写循环时把 open() 移出 try，不可读条目的 OSError 原样抛出",
)
variants["wr_null_raises"] = (
    sub(
        BASE,
        OLD_LOOP,
        """    for path in file_paths:
        try:
            with open(path) as f:
                text = f.read()
        except OSError:
            # Ignore permission errors
            continue
        # Empty and fully commented-out files (see ``ensure_file``) hold no configuration
        if all(not ln.strip() or ln.lstrip().startswith("#") for ln in text.splitlines()):
            continue
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ValueError(f"Could not parse Dask config file {path!r}") from exc
        if not isinstance(data, dict):
            raise ValueError(
                f"Dask config file {path!r} must contain a mapping at the top level, "
                f"got {type(data).__name__}"
            )
        configs.append(data)
""",
    ),
    "按文本判断空文件／全注释；其余解析为 None 的文件（显式 null、只有 '---' 与注释）报错",
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
meta["_base_sha256"] = hashlib.sha256(BASE.encode()).hexdigest()
meta["_gold_inmemory_sha256"] = hashlib.sha256(GOLD.encode()).hexdigest()
(out_dir / "candidates_review.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n")
print(json.dumps({k: (v if k.startswith("_") else v["sha256"][:12]) for k, v in meta.items()}, indent=1))
