p = "/root/slime/slime/rollout/fully_async_rollout.py"
src = open(p).read()
old = '''    def _key(group: list[Sample]) -> int:
        for s in group:
            idx = getattr(s, "index", None)
            if idx is not None:
                return int(idx)
        return 0'''
new = '''    def _key(group) -> int:
        # [rh2 J4c diagnostic patch 2026-07-08] fan-out nested shape
        # (list[list[Sample]]): getattr(list, "index") returns the bound
        # method -> int() TypeError. Flatten recursively; callable guard.
        stack = list(group) if isinstance(group, list) else [group]
        while stack:
            s = stack.pop(0)
            if isinstance(s, list):
                stack = list(s) + stack
                continue
            idx = getattr(s, "index", None)
            if idx is not None and not callable(idx):
                return int(idx)
        return 0'''
assert old in src, "pattern not found"
open(p, "w").write(src.replace(old, new))
print("patched-ok")
