import os, shutil, sys
import coverage
base = "/tmp/r2e_cov_repro"
shutil.rmtree(base, ignore_errors=True)
os.makedirs(base)
bad = 0
for branch in (False, True):
    cov = coverage.Coverage(data_file=os.path.join(base, "data_branch_%s" % branch), branch=branch, config_file=False)
    cov.start()
    exec(compile("a = 1", os.path.join(base, "ok_exec.py"), "exec"), {})
    exec(compile("b = 2", os.path.join(base, "caf\xe9_ok.py"), "exec"), {})
    exec(compile("c = 3", "\udcff.py", "exec"), {})
    cov.stop()
    try:
        cov.save()
    except Exception as exc:
        bad += 1
        print("branch=%s: save() raised %s: %s" % (branch, type(exc).__name__, ascii(str(exc))))
        continue
    files = sorted(cov.get_data().measured_files())
    print("branch=%s: save() OK, measured_files=%s" % (branch, ascii(files)))
    for name in ("ok_exec.py", "caf\xe9_ok.py"):
        if not any(f.endswith(name) for f in files):
            bad += 1
            print("branch=%s: encodable file %s missing from saved data" % (branch, ascii(name)))
sys.exit(1 if bad else 0)
