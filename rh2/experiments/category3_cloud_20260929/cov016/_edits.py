# 候选构造：MODE 选择一种（在 base 的 /testbed 上直接改源码）
import os
from pathlib import Path
mode = os.environ["MODE"]
sq = Path("coverage/sqldata.py"); s = sq.read_text()
HELPER = '''

def _utf8_encodable(filename):
    try:
        filename.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True
'''
LINES_OLD = "            for filename, linenos in iitems(line_data):\n"
ARCS_OLD = "            for filename, arcs in iitems(arc_data):\n"
assert s.count(LINES_OLD) == 1 and s.count(ARCS_OLD) == 1
if mode in ("skip_write", "lines_only"):
    s = s.rstrip("\n") + "\n" + HELPER
    s = s.replace(LINES_OLD, LINES_OLD + "                if not _utf8_encodable(filename):\n                    continue\n")
    if mode == "skip_write":
        s = s.replace(ARCS_OLD, ARCS_OLD + "                if not _utf8_encodable(filename):\n                    continue\n")
    sq.write_text(s)
elif mode == "convert":
    old = '''                    cur = con.execute("insert or replace into file (path) values (?)", (filename,))'''
    assert s.count(old) == 1
    s = s.replace(old, '''                    # Store names that cannot be encoded in UTF-8 in an escaped form.
                    path = filename.encode("utf-8", "backslashreplace").decode("utf-8")
                    cur = con.execute("insert or replace into file (path) values (?)", (path,))''')
    sq.write_text(s)
elif mode == "catch_save":
    ct = Path("coverage/control.py"); c = ct.read_text()
    old = '''    def save(self):
        """Save the collected coverage data to the data file."""
        data = self.get_data()
        data.write()
'''
    assert c.count(old) == 1, "save"
    c = c.replace(old, '''    def save(self):
        """Save the collected coverage data to the data file."""
        try:
            data = self.get_data()
            data.write()
        except UnicodeEncodeError:
            pass
''')
    ct.write_text(c)
elif mode == "ascii_only":
    io = Path("coverage/inorout.py"); t = io.read_text()
    old = "        # No reason found to skip this file.\n        return None\n"
    assert t.count(old) == 1
    t = t.replace(old, '''        if not filename.isascii():
            return "non-ascii filename"

''' + old)
    io.write_text(t)
else:
    raise SystemExit("unknown mode")
