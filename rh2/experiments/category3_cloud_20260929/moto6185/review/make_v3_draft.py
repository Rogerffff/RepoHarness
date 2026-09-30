"""由作者的 revised_test_v2s.patch 生成复核者的修订草案 v3（私有，只作诊断）。

v3 = v2s + 四处，每处一行数据（第 1 处另加 3 行构造），各自直接拦一个复核者候选：
1. 第一组（合法值往返）加“名为 S 的属性在五层 map 之下”。拦 rv_depth4（只把最多两层嵌套 map 的键
   当属性名的阈值型部分修复）。依据：题面 “It could be deeply nested”“It does not matter where”。
2. 第一组加“名为 S 的属性本身是 map，map 里又有成员 S”。拦 rv_scalar_s（S 的值里还有结构即当畸形）。
   依据：题面 “any key inside the Item (including nested ones) is the character 'S'”——值是什么类型不限；
   boto3 资源层写 {'S': {...}} 就是这一形态。v2s 只是因为 rv_scalar_s 沿用了 gold 的父键写法而在
   key_named_m 处附带拦下它，不是直接断言。
3. 第二组（真正的类型错误照旧报错）加“同一个嵌套 map 里，名为 S 的成员排在 N 整数成员之前”。拦
   rv_swallow_attr（逐属性吞错：同一属性内 S 之后的成员不再校验，N 整数被存入）。依据同 v2 第二组：
   公开 P2P test_put_item_wrong_datatype 的非主键嵌套 N 整数用例。v2s 只是因为吞错顺带让畸形 S→dict
   走到内部 AttributeError 而附带拦下它。
4. v2s 的“非主键 S 类型值不能是 dict”由一例改为两例：除 `attr` 外，再用名为 S 的属性。拦 rv_tagparent
   （属性名恰为类型标签时，其值被误当属性名层，畸形 S→dict 不再报错）。依据同 v2s：base 的服务端校验
   与注释、公开 P2P 的非主键嵌套用例；属性叫 S 不应关掉对它自身值的类型校验。
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


# 1、2：第一组
sub('''+    # The issue's examples: an attribute called 'S' holding None, at the top level and
+    # nested inside a map. 'S' is a valid attribute name anywhere in the item, however
+    # deeply nested, and the item is stored as given
''', '''+    # However deeply nested: an attribute called 'S' five maps down
+    five_levels_deep = {"S": {"S": "asdf"}}
+    for name in "EDCBA":
+        five_levels_deep = {name: {"M": five_levels_deep}}
+
+    # The issue's examples: an attribute called 'S' holding None, at the top level and
+    # nested inside a map. 'S' is a valid attribute name anywhere in the item, however
+    # deeply nested and whatever it holds, and the item is stored as given
''')
sub('''+        ("nested_in_list", {"A": {"L": [{"M": {"S": {"N": "1"}}}]}}),
''', '''+        ("nested_in_list", {"A": {"L": [{"M": {"S": {"N": "1"}}}]}}),
+        ("five_levels_deep", five_levels_deep),
+        ("S_holding_a_map", {"S": {"M": {"S": {"S": "asdf"}}}}),
''')
# 3：第二组
sub('''+    # An attribute called 'S' is validated like any other attribute, and does not switch
+    # off the validation of the other attributes (see test_put_item_wrong_datatype)
''', '''+    # An attribute called 'S' is validated like any other attribute, and does not switch
+    # off the validation of the other attributes or map members (see test_put_item_wrong_datatype)
''')
sub('''+        {"S": {"S": "asdf"}, "nested": {"M": {"sth": {"N": 5}}}},
''', '''+        {"S": {"S": "asdf"}, "nested": {"M": {"sth": {"N": 5}}}},
+        {"nested": {"M": {"S": {"S": "asdf"}, "sth": {"N": 5}}}},
''')
# 4：非主键 S→dict
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
# 重算 hunk 头
lines = t.splitlines(keepends=True)
hi = next(i for i, l in enumerate(lines) if l.startswith("@@"))
body = lines[hi + 1:]
old_n = sum(1 for l in body if l.startswith((" ", "-")))
new_n = sum(1 for l in body if l.startswith((" ", "+")))
lines[hi] = re.sub(r"@@ -933,\d+ \+933,\d+ @@", f"@@ -933,{old_n} +933,{new_n} @@", lines[hi])
dst.write_text("".join(lines))
print("written", dst, old_n, new_n)
