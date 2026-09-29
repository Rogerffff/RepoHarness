# 相关错误候选：在 gold 上把配置冲突也当作“无法编码”，于是标准 dataclass 默认值被警告并排除（不再报错，但丢了 default）
from pathlib import Path
import subprocess
subprocess.run(["git", "apply", "/w/gold.patch"], check=True)
p = Path("pydantic/json_schema.py")
s = p.read_text()
old = "        except PydanticSchemaGenerationError:\n"
assert s.count(old) == 1
s = s.replace(old, "        except (PydanticSchemaGenerationError, PydanticUserError):\n")
p.write_text(s)
