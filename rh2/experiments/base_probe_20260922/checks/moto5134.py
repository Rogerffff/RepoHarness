"""Moto5134 行为裁决：EventPattern 的 exists 语义矩阵（显式 null / 缺键 / 字符串 / 对象）+ 评分选集**之外**的回归面
（tests/test_events/test_events.py 全文件，含 archive 规则的 exists:false 用法）。用于 base / gold / Coder 候选 / Qwen 候选对照。
每行 RESULT= 一个 JSON。"""
import json
import subprocess

from moto.events.models import EventPattern

cases = {"null": {"detail": {"foo": None}}, "missing": {"detail": {}}, "string": {"detail": {"foo": "123"}},
         "object": {"detail": {"foo": {"bar": "baz"}}}, "false_bool": {"detail": {"foo": False}}, "zero": {"detail": {"foo": 0}},
         "empty_string": {"detail": {"foo": ""}}}
for exists in (True, False):
    pat = EventPattern.load(json.dumps({"detail": {"foo": [{"exists": exists}]}}))
    for name, ev in cases.items():
        try:
            v = pat.matches_event(ev)
        except Exception as exc:  # noqa: BLE001
            v = f"error:{type(exc).__name__}"
        basis = {"null": "题面：null 视为存在", "missing": "既有公开测试：缺键不存在", "object": "既有公开测试：对象非叶子 → exists:true 不匹配",
                 "string": "既有公开测试"}.get(name, "推知：falsy 叶子值应视为存在（避免误伤 False/0/空串）")
        print("RESULT=" + json.dumps({"case": f"exists_{str(exists).lower()}__{name}", "value": v, "basis": basis}, ensure_ascii=False))
# 评分选集之外的回归面：整份 test_events.py（含 archive / replay 的 exists:false 规则）
p = subprocess.run(["python", "-m", "pytest", "-q", "-x", "--no-header", "-p", "no:cacheprovider", "tests/test_events/test_events.py"],
                   capture_output=True, text=True, timeout=1200)
tail = [ln for ln in p.stdout.splitlines() if ln.strip()][-3:]
print("RESULT=" + json.dumps({"case": "test_events_py_full_file", "value": {"rc": p.returncode, "tail": tail},
                              "basis": "不在冻结 P2P 内；archive 规则依赖 exists:false 对缺键为真"}, ensure_ascii=False))
