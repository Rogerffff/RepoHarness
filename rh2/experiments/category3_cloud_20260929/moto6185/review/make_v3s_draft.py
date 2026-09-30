"""由作者的 revised_test_v2s.patch 生成复核者的 v3s 草案（私有，只作诊断）。

在 v2s 上只加两处：
1. 第一组（合法值往返）加一例：名为 S 的属性在五层 map 之下。拦阈值型部分修复 rv_depth4
   （只把最多两层嵌套 map 的键当属性名）。依据：题面“It could be deeply nested”“does not matter where”。
2. v2s 的“非主键 S 类型值不能是 dict”由一例改为两例：除 `attr` 外，再用名为 S 的属性。
   拦 rv_tagparent（属性名恰为类型标签时，其值被误当属性名层，畸形 S→dict 不再报错）。
   依据同 v2s：base 的服务端校验与注释、公开 P2P test_put_item_wrong_datatype 的非主键嵌套用例；
   题面“S 与其它名字一样”——属性叫 S 不应关掉对它自身值的类型校验。
"""
import re
import sys
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
t = src.read_text()


def sub(old, new):
    global t
    assert t.count(old) == 1, old
    t = t.replace(old, new)


sub('''+    # The issue's examples: an attribute called 'S' holding None, at the top level and
''', '''+    # However deeply nested: an attribute called 'S' five maps down
+    five_levels_deep = {"S": {"S": "asdf"}}
+    for name in "EDCBA":
+        five_levels_deep = {name: {"M": five_levels_deep}}
+
+    # The issue's examples: an attribute called 'S' holding None, at the top level and
''')
sub('''+        ("nested_in_list", {"A": {"L": [{"M": {"S": {"N": "1"}}}]}}),
''', '''+        ("nested_in_list", {"A": {"L": [{"M": {"S": {"N": "1"}}}]}}),
+        ("five_levels_deep", five_levels_deep),
''')
sub('''+    # A value of type S still cannot be a dictionary for a non-key attribute either
+    # (checked server-side, like the nested non-key 'N' in test_put_item_wrong_datatype)
+    with pytest.raises(ClientError) as exc:
+        client.put_item(
+            TableName="without_sk",
+            Item={"pk": {"S": "invalid"}, "attr": {"S": {"S": "asdf"}}},
+        )
+    err = exc.value.response["Error"]
+    assert err["Code"] == "SerializationException"
+    assert err["Message"] == "Start of structure or map found where not expected"
''', '''+    # A value of type S still cannot be a dictionary for a non-key attribute either, whatever the
+    # attribute is called (checked server-side, like the nested non-key 'N' in
+    # test_put_item_wrong_datatype)
+    for attributes in [
+        {"attr": {"S": {"S": "asdf"}}},
+        {"S": {"S": {"S": "asdf"}}},
+    ]:
+        with pytest.raises(ClientError) as exc:
+            client.put_item(
+                TableName="without_sk", Item={"pk": {"S": "invalid"}, **attributes}
+            )
+        err = exc.value.response["Error"]
+        assert err["Code"] == "SerializationException"
+        assert err["Message"] == "Start of structure or map found where not expected"
''')
# 重算 hunk 头的新行数
lines = t.splitlines(keepends=True)
hi = next(i for i, l in enumerate(lines) if l.startswith("@@"))
body = lines[hi + 1:]
old_n = sum(1 for l in body if l.startswith((" ", "-")))
new_n = sum(1 for l in body if l.startswith((" ", "+")))
lines[hi] = re.sub(r"@@ -933,\d+ \+933,\d+ @@", f"@@ -933,{old_n} +933,{new_n} @@", lines[hi])
t = "".join(lines)
dst.write_text(t)
print("written", dst, old_n, new_n)
