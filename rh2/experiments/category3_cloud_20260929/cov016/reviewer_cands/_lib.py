import sys
def rep(path, old, new, count=1):
    s = open(path, encoding="utf-8").read()
    n = s.count(old)
    assert n == count, (path, n, old[:80])
    s = s.replace(old, new)
    open(path, "w", encoding="utf-8").write(s)
