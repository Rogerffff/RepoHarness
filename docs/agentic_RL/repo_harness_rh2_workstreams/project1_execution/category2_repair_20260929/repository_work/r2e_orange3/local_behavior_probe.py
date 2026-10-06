"""本包轻量私有探针：数学转写与隔离函数；不替代真实 Orange/Qt/actor/grader 验收。"""

from __future__ import annotations

import ast
import difflib
import importlib.util
import itertools
import json
import shutil
import subprocess
import tempfile
from bisect import bisect_right
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from prepare_materials import (
    HERE,
    IDS,
    OLD_RESULTS,
    PRIVATE_ROOT,
    PUBLIC_ROOT,
    ROOT,
    record,
    write_json,
)


def patched_text(source: Path, patch: Path | None) -> str:
    if patch is None:
        return source.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="orange3-material-check-") as directory:
        d = Path(directory)
        dst = d / "Orange/widgets/data/owcolor.py"
        dst.parent.mkdir(parents=True)
        shutil.copyfile(source, dst)
        result = subprocess.run(["git", "apply", str(patch)], cwd=d, capture_output=True, text=True, check=False)
        assert result.returncode == 0, f"{patch.name}: {result.stderr}"
        return dst.read_text(encoding="utf-8")


class Desc:
    def __init__(self, name: str):
        self.var = SimpleNamespace(name=name)
        self.name = name

    @classmethod
    def from_dict(cls, var: SimpleNamespace, values: dict):
        desc = cls(var.name)
        desc.name = values.get("rename", var.name)
        return desc, []


def parse_function(text: str, warning: Mock):
    cls = next(n for n in ast.parse(text).body if isinstance(n, ast.ClassDef) and n.name == "OWColor")
    func = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "_parse_var_defs")
    env = {"chain": itertools.chain, "DiscAttrDesc": Desc, "ContAttrDesc": Desc,
           "InvalidFileFormat": type("InvalidFileFormat", (Exception,), {}),
           "QMessageBox": SimpleNamespace(warning=warning)}
    # 执行已读取的本地公开函数片段；外部对象全部由本探针提供。
    exec(compile(ast.Module(body=[func], type_ignores=[]), "isolated_owcolor_function", "exec"), env)  # noqa: S102
    return env["_parse_var_defs"]


def widget(loaded: bool = False):
    return SimpleNamespace(
        data=object() if loaded else None,
        disc_descs=[Desc("iris")] if loaded else [], cont_descs=[],
        disc_model=SimpleNamespace(set_data=Mock()), cont_model=SimpleNamespace(set_data=Mock()),
        commit=SimpleNamespace(now=Mock()),
    )


def check_color(text: str) -> dict:
    result = {}
    msg = Mock()
    parse = parse_function(text, msg)
    w = widget()
    parse(w, {"categorical": {}, "numeric": {}})
    result["empty_no_warning"] = not msg.called
    names_all = ("foo", "bar", "baz", "qux", "quux", "corge", "grault")
    result["named_warnings_1_to_7"] = []
    for n in range(1, 8):
        msg.reset_mock()
        parse(widget(), {"categorical": {name: {} for name in names_all[:n]}, "numeric": {}})
        text_shown = "\n".join(c[0][2] for c in msg.call_args_list)
        named = [name for name in names_all[:n] if name in text_shown]
        result["named_warnings_1_to_7"].append(
            bool(msg.called and (named == list(names_all[:n]) if n <= 2 else bool(named))))
    msg.reset_mock()
    w = widget(loaded=True)
    parse(w, {"categorical": {"iris": {"rename": "species"}, "foo": {}}, "numeric": {"bar": {}}})
    text_shown = "\n".join(c[0][2] for c in msg.call_args_list)
    result["mixed_warns_categorical"] = "foo" in text_shown
    result["mixed_warns_numeric"] = "bar" in text_shown
    result["mixed_applies_matched_rename"] = w.disc_descs[0].name == "species" and w.commit.now.called
    msg.reset_mock()
    parse(widget(), {"categorical": {}, "numeric": {"bar": {}}})
    result["numeric_only_warns"] = msg.called and "bar" in "\n".join(c[0][2] for c in msg.call_args_list)
    result["all_checks_match"] = all(
        all(value) if isinstance(value, list) else bool(value) for value in result.values())
    return result


def main() -> None:
    model_path = ROOT / OLD_RESULTS / IDS["4014f248"] / "static_check_seg3.py"
    spec = importlib.util.spec_from_file_location("known_discretize_model", model_path)
    model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    xs = [i * 1e-12 for i in range(100)]
    expected_bins = [i // 25 for i in range(100)]
    partitions = {}
    for name in ("noop", "gold/C1/pyx_build", "DG", "C3", "C4"):
        points = model.post(name, xs, [1] * 100, 4)
        bins = [bisect_right(points, x) for x in xs]
        partitions[name] = {"points": points, "bin_counts": {str(i): bins.count(i) for i in set(bins)},
                            "new_scale_assertion_matches": bins == expected_bins,
                            "prior_precision_model_matches": model.run(name)[0]}
    assert partitions["gold/C1/pyx_build"]["new_scale_assertion_matches"]
    assert not partitions["C3"]["new_scale_assertion_matches"]

    task_id = IDS["50f6a758"]
    source = ROOT / PUBLIC_ROOT / task_id / "worktree/Orange/widgets/data/owcolor.py"
    candidate_root = ROOT / OLD_RESULTS / task_id / "cands"
    patches = {"noop": None, "gold": ROOT / PRIVATE_ROOT / task_id / "gold.patch"}
    patches.update({name: candidate_root / f"orange3_50f6_{name}.patch" for name in ("K1", "K2", "K3", "K4", "Cdeg")})
    gold = patched_text(source, patches["gold"])
    marker = "            warnings.insert(0, warn)\n"
    assert gold.count(marker) == 1
    k5 = gold.replace(marker, "            warnings.insert(0, 'Unused variable definitions were ignored.')\n", 1)
    k5_path = HERE / "tasks/50f6a758/cands/K5_unnamed_warning.patch"
    k5_path.parent.mkdir(parents=True, exist_ok=True)
    rel = "Orange/widgets/data/owcolor.py"
    k5_path.write_text("diff --git a/" + rel + " b/" + rel + "\n" + "".join(
        difflib.unified_diff(source.read_text().splitlines(keepends=True), k5.splitlines(keepends=True),
                             fromfile="a/" + rel, tofile="b/" + rel)), encoding="utf-8")
    patches["K5"] = k5_path
    colors = {name: {"patch": record(path.relative_to(ROOT)) if path else None,
                     "function_checks": check_color(patched_text(source, path))}
              for name, path in patches.items()}
    assert all(colors[name]["function_checks"]["all_checks_match"] for name in ("gold", "K1"))
    assert not any(colors[name]["function_checks"]["all_checks_match"] for name in ("noop", "K2", "K3", "K4", "Cdeg", "K5"))
    write_json(HERE / "local_behavior_check.json", {
        "as_of": "2026-10-03", "author_self_check": True,
        "scope": "4014已存Cython数学转写；50f6真实补丁应用后抽取_parse_var_defs，数据描述/Qt/model/commit均为替身",
        "discretization_model_source": record(model_path.relative_to(ROOT)),
        "discretization": partitions, "color_function": colors,
        "limits": ["不是Orange模块导入或Qt运行", "不是完整隐藏测试执行", "不是actor或正式评分",
                   "9b54默认/显式multinomial拟合关系未运行"],
        "docker": False, "ssh": False, "formal_reward": None,
    })
    print(json.dumps({"scale_model_rejects_C3": True, "color_function_candidates": len(colors),
                      "scope": "lightweight_private_probe_not_formal_acceptance"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
