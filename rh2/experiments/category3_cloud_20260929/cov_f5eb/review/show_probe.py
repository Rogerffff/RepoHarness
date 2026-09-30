import json, sys
R="/home/user/RepoHarness/rh2/experiments/category3_cloud_20260929/cov_f5eb/review"
keys=["num_branches","num_partial_branches","covered_branches","missing_branches"]
for c in sys.argv[1:]:
    txt=open(f"{R}/logs/probe__{c}.log").read()
    line=[l for l in txt.splitlines() if l.startswith("PROBE_JSON ")]
    if not line:
        print(c, "NO JSON", txt[-1500:]); continue
    d=json.loads(line[0][len("PROBE_JSON "):])
    print("=====", c)
    for k,v in d.items():
        if "error" in v: print(" ",k, v); continue
        t=v.get("totals",{})
        print(" ",k, "meta_branch=",v.get("meta_branch"), "totals:", [t.get(x) for x in keys], "| files:", {f:[s.get(x) for x in keys] for f,s in v.get("files",{}).items()}, {kk:vv for kk,vv in v.items() if kk in ("run_rc","json_rc","load_err")})
