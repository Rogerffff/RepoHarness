"""上轮真实反例/正控 + 新 pretty/rc=0 日志进入当前生产评分与实际组运输。"""
from __future__ import annotations
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/"chainfix_footer_review_20260919"
sys.path.insert(0,str(HERE/"helpers"))
import probe_pytest_shapes as probe
from repoharness2.grading.manager import outer_session_completed_normally, outer_session_summary
from repoharness2.envpack.bundles_v2 import PrivateGradingBundleV2
from repoharness2.envpack.spec_vendor import SPEC_VENDOR_ID_SWEGYM_242429C1,derive_eval_cmd
from repoharness2.envpack import scoring

REFS=[["tests/test_thing.py::test_feature"],["tests/test_thing.py::test_stable"]]
ID_REFS=[[s+"[before]" for s in group] for group in REFS]

def pydantic_parser(f2p,p2p):
    b=PrivateGradingBundleV2(instance_id="pydantic__pydantic-5386",repo="pydantic/pydantic",repo_key_lower="pydantic/pydantic",
        version="2.01",base_commit=probe.old.BASE_COMMIT,test_patch="diff --git a/tests/t.py b/tests/t.py\n--- a/tests/t.py\n+++ b/tests/t.py\n+x\n",
        fail_to_pass=f2p,pass_to_pass=p2p,eval_cmd=derive_eval_cmd(SPEC_VENDOR_ID_SWEGYM_242429C1,"pydantic/pydantic","2.01"),
        spec_vendor_id=SPEC_VENDOR_ID_SWEGYM_242429C1)
    return lambda log:scoring.parse_eval_log_v2(b,log)

def inputs():
    rows={}
    matrix=json.loads((OLD/"matrix/probe_pytest_shapes.json").read_text())
    for name,c in matrix["cases"].items():
        if name.startswith("syntax_"):
            rows[name]={"candidate":c["candidate"],"patch_path":"src/thing.py","before":"VALUE = 1","after":"def feature(:",
                "refs":REFS,"qualified":True,"expected_reward":0.0}
        elif name.startswith("ordinary_"):
            for suffix,after in (("bad","def unused(:"),("clean","marker = 2")):
                rows[name+"_"+suffix]={"candidate":c["candidate"],"patch_path":"src/unused.py","before":"marker = 1","after":after,
                    "refs":REFS,"qualified":True,"expected_reward":None}
        else:
            rows[name]={"candidate":c["candidate"],"patch_path":"src/id_source.py","before":'label = "before"',"after":'label = "after"',
                "refs":ID_REFS,"qualified":False,"expected_reward":0.0}
    extra=json.loads((OLD/"footer_review_result.json").read_text())
    for name,c in extra["cases"].items():
        if name.startswith("outer_collection"):
            rows[name]={"candidate":c["run"],"patch_path":"src/thing.py","before":"VALUE = 1","after":"from rh2_missing_fixture_dependency import VALUE",
                "refs":REFS,"qualified":False,"expected_reward":None}
        elif name=="saved_pytest623":
            rows[name]={"candidate":c["run"],"patch_path":"src/id_source.py","before":'label = "before"',"after":'label = "after"',
                "refs":ID_REFS,"qualified":False,"expected_reward":0.0}
    startup=json.loads((OLD/"startup_control/result.json").read_text())
    for name,rc in (("startup_child_pass",4),("startup_rc_unknown",None)):
        rows[name]={"candidate":{**startup["candidate"],"rc":rc},"patch_path":"src/thing.py","before":"VALUE = 1",
            "after":"from rh2_missing_fixture_dependency import VALUE","refs":REFS,"qualified":False,"expected_reward":None}
    fresh=json.loads((HERE/"pydantic_runtime/pretty_actual_logs.json").read_text())
    rows.update(fresh["cases"])
    return rows

async def main():
    source=probe.digest_sources()
    probe.HERE=HERE/"validation"
    probe.HERE.mkdir()
    result={"method":"旧真实 pytest 9/6 日志 + 新真实 pytest 8/pretty 日志，真实 parser/manager；容器 I/O 使用维护替身","cases":{},"groups":{}}
    rows=inputs()
    base_parser=probe.old.parser_for
    for name,c in rows.items():
        repo=HERE/"input_sources"/name
        probe.old.write(repo,c["patch_path"],c["after"]+"\n")
        pretty=c["candidate"].get("pretty",False)
        try:
            if pretty:probe.old.parser_for=pydantic_parser
            grade=await probe.grade(name,repo,c["candidate"],probe.old.patch(c["patch_path"],c["before"],c["after"]),
                refs=c["refs"],qualified=c["qualified"])
        finally:
            probe.old.parser_for=base_parser
        result["cases"][name]={"expected_reward":c["expected_reward"],"actual_reward":grade["report"]["reward"],
            "grade":grade,"rc":c["candidate"]["rc"],"parser":"pydantic" if pretty else "moto",
            "summary":outer_session_summary(c["candidate"]["stdout"]),
            "normal":outer_session_completed_normally(c["candidate"]["stdout"],c["candidate"]["rc"])}
    import group_transport_probe as transport
    transport.HERE=HERE/"transport"
    spec=importlib.util.spec_from_file_location("footer_close_world",probe.ROOT/"rh2/tests/adapters_miles/conftest.py")
    fixtures=importlib.util.module_from_spec(spec);sys.modules[spec.name]=fixtures;spec.loader.exec_module(fixtures)
    scope=fixtures._vendor_slime_world.__wrapped__();next(scope)
    try:
        world=fixtures._World();world.install_sglang_stub()
        for name in ("captured_pytest_quiet_default","outer_collection_child_pass_quiet","startup_child_pass","saved_pytest623","pretty_outer_zero","pretty_collection_continue"):
            c=rows[name]
            try:
                if c["candidate"].get("pretty",False):probe.old.parser_for=pydantic_parser
                group=await transport.run_group(world,name,bad_log=probe.old._pa_log(c["candidate"]["stdout"],test_rc=c["candidate"]["rc"]),
                    compile_out="",paths={c["patch_path"]:(c["after"]+"\n").encode()},refs=c["refs"],qualified=c["qualified"])
                result["groups"][name]=group
            finally:
                probe.old.parser_for=base_parser
    finally:
        try:next(scope)
        except StopIteration:pass
    assert source==probe.digest_sources()
    result["source_sha256"]=source
    result["mismatches"]=[name for name,c in result["cases"].items() if c["actual_reward"]!=c["expected_reward"]]
    result["group_mismatches"]=[name for name,g in result["groups"].items() if g["group_buffered"]!=(rows[name]["expected_reward"] is not None)]
    (HERE/"replay_result.json").write_text(probe.redact(json.dumps(result,ensure_ascii=False,indent=2))+"\n")
    print(json.dumps({"cases":len(rows),"mismatches":result["mismatches"],"group_mismatches":result["group_mismatches"],
        "groups":{n:{"rewards":[r["reward"] for r in g["reports"]],"buffered":g["group_buffered"]} for n,g in result["groups"].items()}},ensure_ascii=False,indent=2))
    assert not result["mismatches"] and not result["group_mismatches"]

if __name__=="__main__":asyncio.run(main())
