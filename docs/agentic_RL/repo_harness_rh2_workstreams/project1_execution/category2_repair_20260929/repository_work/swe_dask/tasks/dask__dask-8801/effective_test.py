import base64
import builtins
import hashlib
import json
import re
import os
import site
import stat
import subprocess
import sys
import warnings
from collections import OrderedDict
from contextlib import contextmanager

import pytest
import yaml

import dask.config
from dask.config import (
    _get_paths,
    canonical_name,
    collect,
    collect_env,
    collect_yaml,
    config,
    deserialize,
    ensure_file,
    expand_environment_variables,
    get,
    merge,
    refresh,
    rename,
    serialize,
    update,
    update_defaults,
)
from dask.utils import tmpfile


def test_canonical_name():
    c = {"foo-bar": 1, "fizz_buzz": 2}
    assert canonical_name("foo-bar", c) == "foo-bar"
    assert canonical_name("foo_bar", c) == "foo-bar"
    assert canonical_name("fizz-buzz", c) == "fizz_buzz"
    assert canonical_name("fizz_buzz", c) == "fizz_buzz"
    assert canonical_name("new-key", c) == "new-key"
    assert canonical_name("new_key", c) == "new_key"


def test_update():
    a = {"x": 1, "y": {"a": 1}}
    b = {"x": 2, "z": 3, "y": OrderedDict({"b": 2})}
    update(b, a)
    assert b == {"x": 1, "y": {"a": 1, "b": 2}, "z": 3}

    a = {"x": 1, "y": {"a": 1}}
    b = {"x": 2, "z": 3, "y": {"a": 3, "b": 2}}
    update(b, a, priority="old")
    assert b == {"x": 2, "y": {"a": 3, "b": 2}, "z": 3}


def test_merge():
    a = {"x": 1, "y": {"a": 1}}
    b = {"x": 2, "z": 3, "y": {"b": 2}}

    expected = {"x": 2, "y": {"a": 1, "b": 2}, "z": 3}

    c = merge(a, b)
    assert c == expected


def test_collect_yaml_paths():
    a = {"x": 1, "y": {"a": 1}}
    b = {"x": 2, "z": 3, "y": {"b": 2}}

    expected = {"x": 2, "y": {"a": 1, "b": 2}, "z": 3}

    with tmpfile(extension="yaml") as fn1:
        with tmpfile(extension="yaml") as fn2:
            with open(fn1, "w") as f:
                yaml.dump(a, f)
            with open(fn2, "w") as f:
                yaml.dump(b, f)

            config = merge(*collect_yaml(paths=[fn1, fn2]))
            assert config == expected


def test_collect_yaml_dir():
    a = {"x": 1, "y": {"a": 1}}
    b = {"x": 2, "z": 3, "y": {"b": 2}}

    expected = {"x": 2, "y": {"a": 1, "b": 2}, "z": 3}

    with tmpfile() as dirname:
        os.mkdir(dirname)
        with open(os.path.join(dirname, "a.yaml"), mode="w") as f:
            yaml.dump(a, f)
        with open(os.path.join(dirname, "b.yaml"), mode="w") as f:
            yaml.dump(b, f)

        config = merge(*collect_yaml(paths=[dirname]))
        assert config == expected


@contextmanager
def no_read_permissions(path):
    perm_orig = stat.S_IMODE(os.stat(path).st_mode)
    perm_new = perm_orig ^ stat.S_IREAD
    try:
        os.chmod(path, perm_new)
        yield
    finally:
        os.chmod(path, perm_orig)


@pytest.mark.skipif(
    sys.platform == "win32", reason="Can't make writeonly file on windows"
)
@pytest.mark.parametrize("kind", ["directory", "file"])
def test_collect_yaml_permission_errors(tmpdir, kind):
    a = {"x": 1, "y": 2}
    b = {"y": 3, "z": 4}

    dir_path = str(tmpdir)
    a_path = os.path.join(dir_path, "a.yaml")
    b_path = os.path.join(dir_path, "b.yaml")

    with open(a_path, mode="w") as f:
        yaml.dump(a, f)
    with open(b_path, mode="w") as f:
        yaml.dump(b, f)

    if kind == "directory":
        cant_read = dir_path
        expected = {}
    else:
        cant_read = a_path
        expected = b

    with no_read_permissions(cant_read):
        config = merge(*collect_yaml(paths=[dir_path]))
        assert config == expected



DIAGNOSTIC_PREFIX = "RH2_DASK8801_DIAGNOSTIC_V1:"
IMPORT_PREFIX = "RH2_DASK8801_IMPORT_EXCEPTION_V1:"
COMPAT_PREFIX = "RH2_DASK8801_FALSY_COMPAT_V1:"

def visible_exception(exc):
    """仅取 Python 显示的消息、notes、chain、内建异常组；无帧/源码/locals。"""
    issues = []
    seen = set()

    def visit(err, depth):
        if depth > 32 or id(err) in seen:
            issues.append("chain_cycle_or_depth_limit")
            return None
        seen.add(id(err))
        try:
            message = str(err)
            notes = getattr(err, "__notes__", []) if sys.version_info >= (3, 11) else []
            if not isinstance(notes, (list, tuple)) or not all(isinstance(n, str) for n in notes):
                raise ValueError("non_string_notes")
            if len(message) + sum(len(n) for n in notes) > 65536:
                raise ValueError("message_limit")
            exception_type = type(err)
            displayed_type = exception_type.__qualname__
            if exception_type.__module__ not in ("builtins", "__main__"):
                displayed_type = exception_type.__module__ + "." + displayed_type
            node = {"displayed_type": displayed_type, "message": message, "visible_notes": list(notes)}
            cause = err.__cause__
            context = err.__context__
            if cause is not None:
                node["visible_predecessor"] = {"relation": "explicit_cause", "exception": visit(cause, depth + 1)}
            elif context is not None and not err.__suppress_context__:
                node["visible_predecessor"] = {"relation": "displayed_context", "exception": visit(context, depth + 1)}
            group_type = getattr(builtins, "BaseExceptionGroup", ())
            if isinstance(err, group_type):
                node["visible_group_members"] = [visit(child, depth + 1) for child in err.exceptions]
            return node
        except Exception as capture_error:
            issues.append("exception_capture_error:" + type(capture_error).__name__)
            return None
        finally:
            seen.remove(id(err))

    diagnostic = visit(exc, 0)
    return {"visible_exception": diagnostic, "capture_issues": issues}

def encode_marker(prefix, value):
    data = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(data) > 1048576:
        raise ValueError("diagnostic_packet_too_large")
    return prefix + base64.b64encode(data).decode("ascii")

def decode_markers(text, prefix):
    """只收独立物理行；重复/损坏不默默忽略。调用方核期望集合与运行身份。"""
    values, issues = [], []
    for line in text.splitlines():
        if prefix not in line:
            continue
        if not line.startswith(prefix):
            # pytest 源码展示中的字符串不是封包；只接受整行协议。
            continue
        try:
            token = line[len(prefix):]
            if len(token) > 1400000:
                raise ValueError("packet_limit")
            value = json.loads(base64.b64decode(token, validate=True).decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError("packet_not_object")
            values.append(value)
        except (ValueError, UnicodeError, RecursionError) as exc:
            issues.append("invalid_marker:" + type(exc).__name__)
    return values, issues

def file_fact(path):
    try:
        with open(path, "rb") as stream:
            data = stream.read()
        return {"exists": os.path.isfile(path), "readable": True, "content_sha256": hashlib.sha256(data).hexdigest()}
    except OSError as exc:
        return {"exists": os.path.exists(path), "readable": False, "read_error": type(exc).__name__}

def alias_diagnostic(value, aliases):
    if isinstance(value, str):
        # 一次扫描：插入的身份标记不再扫描；原生占位词不能冒充真实文件。
        pieces = []
        for path, alias in sorted(aliases.items(), key=lambda item: -len(item[0])):
            pieces.append(r"(?<![\w./-])" + re.escape(path) + r"(?![\w.-])")
        literal_tokens = ("BAD_FILE", "GOOD_FILE", "FIXTURE_DIR")
        pieces.extend(re.escape(token) for token in literal_tokens)
        pattern = re.compile("|".join(pieces))

        def replace(match):
            text = match.group(0)
            if text in aliases:
                return aliases[text]
            return "UNMATCHED_LITERAL_TOKEN[" + text.encode("utf-8").hex() + "]"

        return pattern.sub(replace, value)
    if isinstance(value, dict):
        return {key: alias_diagnostic(item, aliases) for key, item in value.items()}
    if isinstance(value, list):
        return [alias_diagnostic(item, aliases) for item in value]
    return value

def emit_diagnostic(fixture, entry, bad_path, good_path, before, diagnostic):
    aliases = {bad_path: "BAD_FILE", good_path: "GOOD_FILE", os.path.dirname(bad_path): "FIXTURE_DIR",
               os.path.basename(bad_path): "BAD_FILE", os.path.basename(good_path): "GOOD_FILE"}
    packet = {
        "schema": "dask8801_diagnostic_packet.v1", "case_id": fixture + ":" + entry,
        "before": before, "after": file_fact(bad_path),
        "diagnostic": {"visible_exception": None, "capture_issues": ["capture_pending"]},
    }
    try:
        packet["diagnostic"] = alias_diagnostic(diagnostic, aliases)
        encoded = encode_marker(DIAGNOSTIC_PREFIX, packet)
    except Exception as capture_error:
        # 限额/编码等采集失败不是求解行为失败，不让采集器使 pytest 失败。
        packet["diagnostic"] = {"visible_exception": None,
                                "capture_issues": ["diagnostic_encoding_error:" + type(capture_error).__name__]}
        encoded = encode_marker(DIAGNOSTIC_PREFIX, packet)
    print(encoded)

IMPORT_CAPTURE_PROGRAM = 'import sys, base64, builtins, json\ndef visible_exception(exc):\n    """仅取 Python 显示的消息、notes、chain、内建异常组；无帧/源码/locals。"""\n    issues = []\n    seen = set()\n\n    def visit(err, depth):\n        if depth > 32 or id(err) in seen:\n            issues.append("chain_cycle_or_depth_limit")\n            return None\n        seen.add(id(err))\n        try:\n            message = str(err)\n            notes = getattr(err, "__notes__", []) if sys.version_info >= (3, 11) else []\n            if not isinstance(notes, (list, tuple)) or not all(isinstance(n, str) for n in notes):\n                raise ValueError("non_string_notes")\n            if len(message) + sum(len(n) for n in notes) > 65536:\n                raise ValueError("message_limit")\n            exception_type = type(err)\n            displayed_type = exception_type.__qualname__\n            if exception_type.__module__ not in ("builtins", "__main__"):\n                displayed_type = exception_type.__module__ + "." + displayed_type\n            node = {"displayed_type": displayed_type, "message": message, "visible_notes": list(notes)}\n            cause = err.__cause__\n            context = err.__context__\n            if cause is not None:\n                node["visible_predecessor"] = {"relation": "explicit_cause", "exception": visit(cause, depth + 1)}\n            elif context is not None and not err.__suppress_context__:\n                node["visible_predecessor"] = {"relation": "displayed_context", "exception": visit(context, depth + 1)}\n            group_type = getattr(builtins, "BaseExceptionGroup", ())\n            if isinstance(err, group_type):\n                node["visible_group_members"] = [visit(child, depth + 1) for child in err.exceptions]\n            return node\n        except Exception as capture_error:\n            issues.append("exception_capture_error:" + type(capture_error).__name__)\n            return None\n        finally:\n            seen.remove(id(err))\n\n    diagnostic = visit(exc, 0)\n    return {"visible_exception": diagnostic, "capture_issues": issues}\n\ndef encode_marker(prefix, value):\n    data = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")\n    if len(data) > 1048576:\n        raise ValueError("diagnostic_packet_too_large")\n    return prefix + base64.b64encode(data).decode("ascii")\ndef trusted_exception_hook(kind, exc, tb):\n    sys.__excepthook__(kind, exc, tb)\n    print(encode_marker("RH2_DASK8801_IMPORT_EXCEPTION_V1:", visible_exception(exc)), file=sys.stderr)\nsys.excepthook = trusted_exception_hook\nimport dask\n'

def _collect_yaml_error(paths):
    with pytest.raises(Exception) as rec:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            collect_yaml(paths=paths)
    return rec.value


def test_collect_yaml_malformed_file(tmpdir):
    dir_path = str(tmpdir)
    fil_path = os.path.join(dir_path, "a.yaml")
    other_path = os.path.join(dir_path, "b.yaml")
    os.mkdir(os.path.join(dir_path, "0.yaml"))
    with open(other_path, "wb") as f:
        f.write(b"x: 1\n")
    for fixture, content in [("syntax_brace", b"{"), ("syntax_tab", b"a: 1\n\tb: 2\n")]:
        with open(fil_path, "wb") as f:
            f.write(content)
        with pytest.raises(yaml.YAMLError):
            yaml.safe_load(content.decode())
        for entry, paths in [("directory", [dir_path]), ("file", [fil_path])]:
            before = file_fact(fil_path)
            err = _collect_yaml_error(paths)
            emit_diagnostic(fixture, entry, fil_path, other_path, before, visible_exception(err))


def test_collect_yaml_no_top_level_dict(tmpdir):
    dir_path = str(tmpdir)
    fil_path = os.path.join(dir_path, "a.yaml")
    other_path = os.path.join(dir_path, "b.yaml")
    os.mkdir(os.path.join(dir_path, "0.yaml"))
    with open(other_path, "wb") as f:
        f.write(b"x: 1\n")
    for content in [b"", b"# x: 1\n", b"null\n", b"---\n", b"{}"]:
        with open(fil_path, "wb") as f:
            f.write(content)
        assert merge(*collect_yaml(paths=[dir_path])) == {"x": 1}
    # 已裁定的兼容边界：接受为空配置，或抛出可见且真实的内容诊断。
    for fixture, content in [("falsy_list", b"[]"), ("falsy_str", b'""'),
                             ("falsy_int", b"0"), ("falsy_float", b"0.0"),
                             ("falsy_bool", b"false")]:
        with open(fil_path, "wb") as f:
            f.write(content)
        for entry, paths in [("directory", [dir_path]), ("file", [fil_path])]:
            before = file_fact(fil_path)
            try:
                configs = collect_yaml(paths=paths)
            except Exception as err:
                branch = "diagnostic_failure"
                emit_diagnostic(fixture, entry, fil_path, other_path, before, visible_exception(err))
            else:
                branch = "empty_configuration"
                assert isinstance(configs, list) and all(isinstance(c, dict) for c in configs)
                assert merge(*configs) == ({"x": 1} if entry == "directory" else {})
            print(encode_marker(COMPAT_PREFIX, {
                "schema": "dask8801_falsy_branch.v1", "case_id": fixture + ":" + entry,
                "branch": branch, "before": before, "after": file_fact(fil_path)}))
    for fixture, content in [("nonmapping_list", b"[1234]"), ("nonmapping_str", b"hello"),
                             ("nonmapping_int", b"1234"), ("nonmapping_float", b"1.5")]:
        with open(fil_path, "wb") as f:
            f.write(content)
        for entry, paths in [("directory", [dir_path]), ("file", [fil_path])]:
            before = file_fact(fil_path)
            err = _collect_yaml_error(paths)
            emit_diagnostic(fixture, entry, fil_path, other_path, before, visible_exception(err))

    with open(fil_path, "wb") as f:
        f.write(b"hello")
    before = file_fact(fil_path)
    env = dict(os.environ, DASK_CONFIG=dir_path,
               DASK_ROOT_CONFIG=os.path.join(dir_path, "no-such-dir"),
               HOME=os.path.join(dir_path, "no-such-home"))
    proc = subprocess.run([sys.executable, "-c", IMPORT_CAPTURE_PROGRAM], env=env,
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode != 0
    # 打印原始 stderr 以供运行审计，宿主仅将封包的可见消息送语义裁决。
    print("RH2_DASK8801_RAW_IMPORT_STDERR_BEGIN")
    for line in proc.stderr.splitlines():
        print("RAW_IMPORT | " + line)
    print("RH2_DASK8801_RAW_IMPORT_STDERR_END")
    diagnostics, issues = decode_markers(proc.stderr, IMPORT_PREFIX)
    diagnostic = diagnostics[0] if len(diagnostics) == 1 and not issues else {
        "visible_exception": None, "capture_issues": issues + ["import_exception_packet_missing_or_duplicated"]}
    emit_diagnostic("nonmapping_str", "import", fil_path, other_path, before, diagnostic)


def test_env():
    env = {
        "DASK_A_B": "123",
        "DASK_C": "True",
        "DASK_D": "hello",
        "DASK_E__X": "123",
        "DASK_E__Y": "456",
        "DASK_F": '[1, 2, "3"]',
        "DASK_G": "/not/parsable/as/literal",
        "FOO": "not included",
    }

    expected = {
        "a_b": 123,
        "c": True,
        "d": "hello",
        "e": {"x": 123, "y": 456},
        "f": [1, 2, "3"],
        "g": "/not/parsable/as/literal",
    }

    res = collect_env(env)
    assert res == expected


def test_collect():
    a = {"x": 1, "y": {"a": 1}}
    b = {"x": 2, "z": 3, "y": {"b": 2}}
    env = {"DASK_W": 4}

    expected = {"w": 4, "x": 2, "y": {"a": 1, "b": 2}, "z": 3}

    with tmpfile(extension="yaml") as fn1:
        with tmpfile(extension="yaml") as fn2:
            with open(fn1, "w") as f:
                yaml.dump(a, f)
            with open(fn2, "w") as f:
                yaml.dump(b, f)

            config = collect([fn1, fn2], env=env)
            assert config == expected


def test_collect_env_none(monkeypatch):
    monkeypatch.setenv("DASK_FOO", "bar")
    config = collect([])
    assert config == {"foo": "bar"}


def test_get():
    d = {"x": 1, "y": {"a": 2}}

    assert get("x", config=d) == 1
    assert get("y.a", config=d) == 2
    assert get("y.b", 123, config=d) == 123
    with pytest.raises(KeyError):
        get("y.b", config=d)


def test_ensure_file(tmpdir):
    a = {"x": 1, "y": {"a": 1}}
    b = {"x": 123}

    source = os.path.join(str(tmpdir), "source.yaml")
    dest = os.path.join(str(tmpdir), "dest")
    destination = os.path.join(dest, "source.yaml")

    with open(source, "w") as f:
        yaml.dump(a, f)

    ensure_file(source=source, destination=dest, comment=False)

    with open(destination) as f:
        result = yaml.safe_load(f)
    assert result == a

    # don't overwrite old config files
    with open(source, "w") as f:
        yaml.dump(b, f)

    ensure_file(source=source, destination=dest, comment=False)

    with open(destination) as f:
        result = yaml.safe_load(f)
    assert result == a

    os.remove(destination)

    # Write again, now with comments
    ensure_file(source=source, destination=dest, comment=True)

    with open(destination) as f:
        text = f.read()
    assert "123" in text

    with open(destination) as f:
        result = yaml.safe_load(f)
    assert not result


def test_set():
    with dask.config.set(abc=123):
        assert config["abc"] == 123
        with dask.config.set(abc=456):
            assert config["abc"] == 456
        assert config["abc"] == 123

    assert "abc" not in config

    with dask.config.set({"abc": 123}):
        assert config["abc"] == 123
    assert "abc" not in config

    with dask.config.set({"abc.x": 1, "abc.y": 2, "abc.z.a": 3}):
        assert config["abc"] == {"x": 1, "y": 2, "z": {"a": 3}}
    assert "abc" not in config

    d = {}
    dask.config.set({"abc.x": 123}, config=d)
    assert d["abc"]["x"] == 123


def test_set_kwargs():
    with dask.config.set(foo__bar=1, foo__baz=2):
        assert config["foo"] == {"bar": 1, "baz": 2}
    assert "foo" not in config

    # Mix kwargs and dict, kwargs override
    with dask.config.set({"foo.bar": 1, "foo.baz": 2}, foo__buzz=3, foo__bar=4):
        assert config["foo"] == {"bar": 4, "baz": 2, "buzz": 3}
    assert "foo" not in config

    # Mix kwargs and nested dict, kwargs override
    with dask.config.set({"foo": {"bar": 1, "baz": 2}}, foo__buzz=3, foo__bar=4):
        assert config["foo"] == {"bar": 4, "baz": 2, "buzz": 3}
    assert "foo" not in config


def test_set_nested():
    with dask.config.set({"abc": {"x": 123}}):
        assert config["abc"] == {"x": 123}
        with dask.config.set({"abc.y": 456}):
            assert config["abc"] == {"x": 123, "y": 456}
        assert config["abc"] == {"x": 123}
    assert "abc" not in config


def test_set_hard_to_copyables():
    import threading

    with dask.config.set(x=threading.Lock()):
        with dask.config.set(y=1):
            pass


@pytest.mark.parametrize("mkdir", [True, False])
def test_ensure_file_directory(mkdir, tmpdir):
    a = {"x": 1, "y": {"a": 1}}

    source = os.path.join(str(tmpdir), "source.yaml")
    dest = os.path.join(str(tmpdir), "dest")

    with open(source, "w") as f:
        yaml.dump(a, f)

    if mkdir:
        os.mkdir(dest)

    ensure_file(source=source, destination=dest)

    assert os.path.isdir(dest)
    assert os.path.exists(os.path.join(dest, "source.yaml"))


def test_ensure_file_defaults_to_DASK_CONFIG_directory(tmpdir):
    a = {"x": 1, "y": {"a": 1}}
    source = os.path.join(str(tmpdir), "source.yaml")
    with open(source, "w") as f:
        yaml.dump(a, f)

    destination = os.path.join(str(tmpdir), "dask")
    PATH = dask.config.PATH
    try:
        dask.config.PATH = destination
        ensure_file(source=source)
    finally:
        dask.config.PATH = PATH

    assert os.path.isdir(destination)
    [fn] = os.listdir(destination)
    assert os.path.split(fn)[1] == os.path.split(source)[1]


def test_rename():
    aliases = {"foo_bar": "foo.bar"}
    config = {"foo-bar": 123}
    rename(aliases, config=config)
    assert config == {"foo": {"bar": 123}}


def test_refresh():
    defaults = []
    config = {}

    update_defaults({"a": 1}, config=config, defaults=defaults)
    assert config == {"a": 1}

    refresh(paths=[], env={"DASK_B": "2"}, config=config, defaults=defaults)
    assert config == {"a": 1, "b": 2}

    refresh(paths=[], env={"DASK_C": "3"}, config=config, defaults=defaults)
    assert config == {"a": 1, "c": 3}


@pytest.mark.parametrize(
    "inp,out",
    [
        ("1", "1"),
        (1, 1),
        ("$FOO", "foo"),
        ([1, "$FOO"], [1, "foo"]),
        ((1, "$FOO"), (1, "foo")),
        ({1, "$FOO"}, {1, "foo"}),
        ({"a": "$FOO"}, {"a": "foo"}),
        ({"a": "A", "b": [1, "2", "$FOO"]}, {"a": "A", "b": [1, "2", "foo"]}),
    ],
)
def test_expand_environment_variables(monkeypatch, inp, out):
    monkeypatch.setenv("FOO", "foo")
    assert expand_environment_variables(inp) == out


def test_env_var_canonical_name(monkeypatch):
    value = 3
    monkeypatch.setenv("DASK_A_B", str(value))
    d = {}
    dask.config.refresh(config=d)
    assert get("a_b", config=d) == value
    assert get("a-b", config=d) == value


def test_get_set_canonical_name():
    c = {"x-y": {"a_b": 123}}

    keys = ["x_y.a_b", "x-y.a-b", "x_y.a-b"]
    for k in keys:
        assert dask.config.get(k, config=c) == 123

    with dask.config.set({"x_y": {"a-b": 456}}, config=c):
        for k in keys:
            assert dask.config.get(k, config=c) == 456

    # No change to new keys in sub dicts
    with dask.config.set({"x_y": {"a-b": {"c_d": 1}, "e-f": 2}}, config=c):
        assert dask.config.get("x_y.a-b", config=c) == {"c_d": 1}
        assert dask.config.get("x_y.e_f", config=c) == 2


@pytest.mark.parametrize("key", ["custom_key", "custom-key"])
def test_get_set_roundtrip(key):
    value = 123
    with dask.config.set({key: value}):
        assert dask.config.get("custom_key") == value
        assert dask.config.get("custom-key") == value


def test_merge_None_to_dict():
    assert dask.config.merge({"a": None, "c": 0}, {"a": {"b": 1}}) == {
        "a": {"b": 1},
        "c": 0,
    }


def test_core_file():
    assert "temporary-directory" in dask.config.config
    assert "dataframe" in dask.config.config
    assert "shuffle-compression" in dask.config.get("dataframe")


def test_schema():
    jsonschema = pytest.importorskip("jsonschema")

    config_fn = os.path.join(os.path.dirname(__file__), "..", "dask.yaml")
    schema_fn = os.path.join(os.path.dirname(__file__), "..", "dask-schema.yaml")

    with open(config_fn) as f:
        config = yaml.safe_load(f)

    with open(schema_fn) as f:
        schema = yaml.safe_load(f)

    jsonschema.validate(config, schema)


def test_schema_is_complete():
    config_fn = os.path.join(os.path.dirname(__file__), "..", "dask.yaml")
    schema_fn = os.path.join(os.path.dirname(__file__), "..", "dask-schema.yaml")

    with open(config_fn) as f:
        config = yaml.safe_load(f)

    with open(schema_fn) as f:
        schema = yaml.safe_load(f)

    def test_matches(c, s):
        for k, v in c.items():
            if list(c) != list(s["properties"]):
                raise ValueError(
                    "\nThe dask.yaml and dask-schema.yaml files are not in sync.\n"
                    "This usually happens when we add a new configuration value,\n"
                    "but don't add the schema of that value to the dask-schema.yaml file\n"
                    "Please modify these files to include the missing values: \n\n"
                    "    dask.yaml:        {}\n"
                    "    dask-schema.yaml: {}\n\n"
                    "Examples in these files should be a good start, \n"
                    "even if you are not familiar with the jsonschema spec".format(
                        sorted(c), sorted(s["properties"])
                    )
                )
            if isinstance(v, dict):
                test_matches(c[k], s["properties"][k])

    test_matches(config, schema)


def test_deprecations():
    with pytest.warns(Warning) as info:
        with dask.config.set(fuse_ave_width=123):
            assert dask.config.get("optimization.fuse.ave-width") == 123

    assert "optimization.fuse.ave-width" in str(info[0].message)


def test_get_override_with():
    with dask.config.set({"foo": "bar"}):
        # If override_with is None get the config key
        assert dask.config.get("foo") == "bar"
        assert dask.config.get("foo", override_with=None) == "bar"

        # Otherwise pass the default straight through
        assert dask.config.get("foo", override_with="baz") == "baz"
        assert dask.config.get("foo", override_with=False) is False
        assert dask.config.get("foo", override_with=True) is True
        assert dask.config.get("foo", override_with=123) == 123
        assert dask.config.get("foo", override_with={"hello": "world"}) == {
            "hello": "world"
        }
        assert dask.config.get("foo", override_with=["one"]) == ["one"]


def test_config_serialization():
    # Use context manager without changing the value to ensure test side effects are restored
    with dask.config.set({"array.svg.size": dask.config.get("array.svg.size")}):

        # Take a round trip through the serialization
        serialized = serialize({"array": {"svg": {"size": 150}}})
        config = deserialize(serialized)

        dask.config.update(dask.config.global_config, config)
        assert dask.config.get("array.svg.size") == 150


def test_config_inheritance():
    config = collect_env(
        {"DASK_INTERNAL_INHERIT_CONFIG": serialize({"array": {"svg": {"size": 150}}})}
    )
    assert dask.config.get("array.svg.size", config=config) == 150


def test__get_paths(monkeypatch):
    # These settings are used by Dask's config system. We temporarily
    # remove them to avoid interference from the machine where tests
    # are being run.
    monkeypatch.delenv("DASK_CONFIG", raising=False)
    monkeypatch.delenv("DASK_ROOT_CONFIG", raising=False)
    monkeypatch.setattr(site, "PREFIXES", [])

    expected = [
        "/etc/dask",
        os.path.join(sys.prefix, "etc", "dask"),
        os.path.join(os.path.expanduser("~"), ".config", "dask"),
    ]
    paths = _get_paths()
    assert paths == expected
    assert len(paths) == len(set(paths))  # No duplicate paths

    with monkeypatch.context() as m:
        m.setenv("DASK_CONFIG", "foo-bar")
        paths = _get_paths()
        assert paths == expected + ["foo-bar"]
        assert len(paths) == len(set(paths))

    with monkeypatch.context() as m:
        m.setenv("DASK_ROOT_CONFIG", "foo-bar")
        paths = _get_paths()
        assert paths == ["foo-bar"] + expected[1:]
        assert len(paths) == len(set(paths))

    with monkeypatch.context() as m:
        prefix = os.path.join("include", "this", "path")
        m.setattr(site, "PREFIXES", site.PREFIXES + [prefix])
        paths = _get_paths()
        assert os.path.join(prefix, "etc", "dask") in paths
        assert len(paths) == len(set(paths))


def test_default_search_paths():
    # Ensure _get_paths() is used for default paths
    assert dask.config.paths == _get_paths()
