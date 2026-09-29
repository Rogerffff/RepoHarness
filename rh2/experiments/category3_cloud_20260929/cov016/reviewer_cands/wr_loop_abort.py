# wrong: catch UnicodeEncodeError around the per-file loop *inside* the connection block:
# no rollback, but every file after the first unencodable one is silently dropped.
P = "coverage/sqldata.py"
s = open(P, encoding="utf-8").read()
def wrap(s, start_marker, end_marker):
    i = s.index(start_marker)
    j = s.index(end_marker, i)
    block = s[i:j].rstrip("\n")
    body = "\n".join(("    " + l) if l.strip() else l for l in block.split("\n"))
    new = "            try:\n" + body + "\n            except UnicodeEncodeError:\n                pass\n\n"
    return s[:i] + new + s[j:]
s = wrap(s, "            for filename, linenos in iitems(line_data):\n", "    def add_arcs(")
s = wrap(s, "            for filename, arcs in iitems(arc_data):\n", "    def _choose_lines_or_arcs(")
open(P, "w", encoding="utf-8").write(s)
