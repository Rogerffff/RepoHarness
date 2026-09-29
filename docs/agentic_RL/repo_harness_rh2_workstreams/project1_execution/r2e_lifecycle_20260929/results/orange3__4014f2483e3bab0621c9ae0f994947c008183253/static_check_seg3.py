"""orange3 4014f248 R-c 静态核对（2026-09-29，修订执行者）。纯 Python，不导入 Orange 或 numpy，不运行项目代码。

按 base 的 Orange/preprocess/_discretize.pyx:12-57 逐行转写 split_eq_freq（IEEE double，就近取偶），
再套各候选的后处理，检查修订后 test_below_precision 三段断言（HT' 第 57、66、78、80、81 行）。
np.digitize(x, bins)（right=False、bins 递增）等价于 bisect_right(bins, x)；切点为空时
Discretizer.digitize 返回全 0（W/Orange/preprocess/discretize.py:40）。
候选：noop；gold / C1 / 重编补丁（都等价于 sorted(set(base))）；DG；C3；C4；以及三种只做静态判断的写法。
用法：python3 static_check_seg3.py
"""
import math
import sys
from bisect import bisect_right

eps = sys.float_info.epsilon


def split_eq_freq(values, counts, n):
    llen = len(values)
    if n >= llen:
        return [(v1 + v2) / 2 for v1, v2 in zip(values, values[1:])]
    N = float(sum(counts))
    toGo, inthis, prevel, inone, points = n, 0.0, -1.0, N / n, []
    for i in range(llen):
        v, k = values[i], counts[i]
        if toGo <= 1:
            break
        inthis += k
        if inthis < inone or i == 0:
            prevel = v
        else:
            if i < llen - 1 and inthis - inone < k / 2:
                vn = values[i + 1]
                points.append((vn + v) / 2)
                N -= inthis
                inthis = 0
                prevel = vn
            else:
                points.append((prevel + v) / 2)
                N -= inthis - k
                inthis = k
                prevel = v
            toGo -= 1
            if toGo:
                inone = N / toGo
    return points


def post(name, vals, cnts, n):
    base = split_eq_freq(vals, cnts, n)
    if name == "noop":
        return base
    if name == "gold/C1/pyx_build":
        return sorted(set(base))
    if name == "DG":
        return [] if len(base) != len(set(base)) else base
    if name == "C3":
        return sorted(set(round(float(p), 10) for p in base))
    if name == "C4":
        return sorted(set(base)) if n >= len(vals) else base
    if name == "static:nextafter":
        out = []
        for p in base:
            if out and p <= out[-1]:
                p = math.nextafter(out[-1], math.inf)
            out.append(p)
        return out
    if name == "static:drop_colliding":
        return [p for p in base if base.count(p) == 1]
    if name == "static:retry_smaller_n":
        m = n
        while True:
            p = split_eq_freq(vals, cnts, m)
            if len(set(p)) == len(p):
                return p
            m -= 1
    raise ValueError(name)


SEGMENTS = (
    ("seg1 HT':50-57", [1.0, 1 + eps, 1 + 2 * eps, 1 + 3 * eps], 4, False),
    ("seg2 HT':59-66", [1 + i * eps for i in range(10)], 8, False),
    ("seg3 HT':68-81", [0.0, 1.0, 1 + eps, 1 + 2 * eps, 1 + 3 * eps, 2.0], 6, True),
)


def run(name):
    notes = []
    for label, xs, n, order_check in SEGMENTS:
        vals = sorted(set(xs))
        cnts = [xs.count(v) for v in vals]
        pts = post(name, vals, cnts, n)
        lp = list(pts)
        if not all(lo < hi for lo, hi in zip([-math.inf] + lp, lp + [math.inf])):
            return False, notes + ["%s: _fmt_interval AssertionError (discretize.py:53)" % label]
        if len(set(pts)) != len(pts):
            return False, notes + ["%s: points not unique" % label]
        if order_check:
            bins = [bisect_right(pts, x) if pts else 0 for x in xs]
            if not bins[0] < min(bins[1:5]):
                return False, notes + ["%s: assertLess fails (HT':80), bins=%s" % (label, bins)]
            if not bins[5] > max(bins[1:5]):
                return False, notes + ["%s: assertGreater fails (HT':81), bins=%s" % (label, bins)]
            notes.append("%s ok, points=%s, bins=%s" % (label, [p.hex() for p in pts], bins))
        else:
            notes.append("%s ok" % label)
    return True, notes


if __name__ == "__main__":
    vals = [0.0, 1.0, 1 + eps, 1 + 2 * eps, 1 + 3 * eps, 2.0]
    print("seg3 base split_eq_freq:", [p.hex() for p in split_eq_freq(vals, [1] * 6, 6)])
    for name in ("noop", "gold/C1/pyx_build", "DG", "C3", "C4",
                 "static:nextafter", "static:drop_colliding", "static:retry_smaller_n"):
        ok, notes = run(name)
        print("%-24s %-4s %s" % (name, "PASS" if ok else "FAIL", " | ".join(notes)))
