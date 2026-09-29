# 上游式第二正对照：gold 加上游 pydantic 2.7.1（#9287）的一处改动，按类型是否带 config 分流，
# 与 2.7.1 wheel 中的 encode_default 逐字相同（独立复核附录的构造）
from pathlib import Path
import subprocess
subprocess.run(["git", "apply", "/w/gold.patch"], check=True)
p = Path("pydantic/json_schema.py")
s = p.read_text()
old_imp = "        from .type_adapter import TypeAdapter\n"
old_if = "                if hasattr(dft, '__pydantic_serializer__')\n"
assert s.count(old_imp) == 1 and s.count(old_if) == 1, (s.count(old_imp), s.count(old_if))
s = s.replace(old_imp, "        from .type_adapter import TypeAdapter, _type_has_config\n")
s = s.replace(old_if, "                if _type_has_config(type(dft))\n")
p.write_text(s)
