# N1（盲写）：按题面建议，给 libs 块里的每个 cc_import 加 alwayslink = True
import re, sys
p = "conan/tools/google/bazeldeps.py"
s = open(p).read()
old = '''            cc_import(
                name = "{{ libname }}_precompiled",
                {{ library_type }} = "{{ filepath }}"
            )
'''
new = '''            cc_import(
                name = "{{ libname }}_precompiled",
                {{ library_type }} = "{{ filepath }}",
                alwayslink = True,
            )
'''
assert s.count(old) == 1
open(p, "w").write(s.replace(old, new))
