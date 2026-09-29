# 按 R2E 线修订计划的描述重建对照候选（原补丁在本地 runs/，云端没有）：
# CE1 按消息去重；CE3 按 slug 去重（独立集合，不动 disable_warnings）；CE4 第一次 once 之后所有 once 警告都不显示
import os
from pathlib import Path
mode = os.environ["MODE"]
p = Path("coverage/control.py"); s = p.read_text()
old_sig = "    def _warn(self, msg, slug=None):\n"
old_body = '''        if slug in self.config.disable_warnings:
            # Don't issue the warning
            return
'''
old_tail = '''        sys.stderr.write("Coverage.py warning: %s\\n" % msg)

    def get_option(self, option_name):
'''
assert s.count(old_sig) == 1 and s.count(old_body) == 1 and s.count(old_tail) == 1
s = s.replace(old_sig, "    def _warn(self, msg, slug=None, once=False):\n")
if mode == "CE1":
    key, pre = "msg", ""
elif mode == "CE3":
    key, pre = "slug", ""
elif mode == "CE4":
    key, pre = None, ""
if mode in ("CE1", "CE3"):
    s = s.replace(old_body, old_body + f'''        shown = self.__dict__.setdefault("_c3_once_shown", set())
        if once and {key} in shown:
            return
''')
    s = s.replace(old_tail, f'''        sys.stderr.write("Coverage.py warning: %s\\n" % msg)
        if once:
            shown.add({"orig_msg" if key == "msg" else "slug"})

    def get_option(self, option_name):
''')
    if key == "msg":
        s = s.replace(old_body, old_body + "        orig_msg = msg\n", 1)
else:
    s = s.replace(old_body, old_body + '''        if once and getattr(self, "_c3_any_once", False):
            return
''')
    s = s.replace(old_tail, '''        sys.stderr.write("Coverage.py warning: %s\\n" % msg)
        if once:
            self._c3_any_once = True

    def get_option(self, option_name):
''')
p.write_text(s)
