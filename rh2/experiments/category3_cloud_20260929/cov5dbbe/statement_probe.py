# 修订题面（选项 A）逐句核对：同 slug 不同消息只显示第一条；不同 slug 各显示一次；原例照抄
import io, json, sys, contextlib, tempfile, os
os.chdir(tempfile.mkdtemp())
import coverage
def run(calls):
    cov = coverage.Coverage()
    cov.load()
    buf = io.StringIO()
    try:
        with contextlib.redirect_stderr(buf):
            for m, s in calls:
                cov._warn(m, slug=s, once=True)
    except Exception as e:
        return "EXC %s: %s" % (type(e).__name__, e)
    return [l for l in buf.getvalue().splitlines() if l.strip()]
res = {
  "example_same_slug_two_msgs": run([("Warning, warning 1!", "bot"), ("Warning, warning 2!", "bot")]),
  "different_slugs": run([("first", "slug-a"), ("second", "slug-b")]),
  "same_msg_same_slug_twice": run([("again", "bot"), ("again", "bot")]),
}
print(json.dumps(res, ensure_ascii=False))
