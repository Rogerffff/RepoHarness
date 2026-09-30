"""由作者的 revised_test_v2.patch 生成复核者的 v3 草案（私有，只作诊断）。

在 v2 上只加两处（各一行数据，外加注释措辞）：
1. 第一组（合法值往返）加一例：名为 S 的属性本身是一个 map，map 里又有成员 S。
   拦 rv_scalar_s（“S 的值里还有结构即畸形”）。依据：题面“any key inside the Item (including nested ones)”，
   S 是属性名时它的值可以是任何类型；boto3 资源层写 {'S': {...}} 就是这种形态。
2. 第二组（真正的类型错误照旧报错）加一例：同一个嵌套 map 里，名为 S 的成员排在 N 整数成员之前。
   拦 rv_swallow_attr（逐属性吞错，同一属性内 S 之后的成员不再校验）。依据同 v2 第二组：
   公开 P2P test_put_item_wrong_datatype 的非主键嵌套 N 整数用例；名为 S 的成员不应关掉其它成员的校验。
"""
import sys
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
t = src.read_text()


def sub(old, new):
    global t
    assert t.count(old) == 1, old
    t = t.replace(old, new)


sub("@@ -933,12 +933,49 @@", "@@ -933,12 +933,51 @@")
sub('''+    # nested inside a map. 'S' is a valid attribute name anywhere in the item, however
+    # deeply nested, and the item is stored as given
''', '''+    # nested inside a map. 'S' is a valid attribute name anywhere in the item, however
+    # deeply nested and whatever it holds, and the item is stored as given
''')
sub('''+        ("nested_in_list", {"A": {"L": [{"M": {"S": {"N": "1"}}}]}}),
''', '''+        ("nested_in_list", {"A": {"L": [{"M": {"S": {"N": "1"}}}]}}),
+        ("S_holding_a_map", {"S": {"M": {"S": {"S": "asdf"}}}}),
''')
sub('''+    # An attribute called 'S' is validated like any other attribute, and does not switch
+    # off the validation of the other attributes (see test_put_item_wrong_datatype)
''', '''+    # An attribute called 'S' is validated like any other attribute, and does not switch
+    # off the validation of the other attributes or map members (see test_put_item_wrong_datatype)
''')
sub('''+        {"S": {"S": "asdf"}, "nested": {"M": {"sth": {"N": 5}}}},
''', '''+        {"S": {"S": "asdf"}, "nested": {"M": {"sth": {"N": 5}}}},
+        {"nested": {"M": {"S": {"S": "asdf"}, "sth": {"N": 5}}}},
''')
dst.write_text(t)
print("written", dst)
