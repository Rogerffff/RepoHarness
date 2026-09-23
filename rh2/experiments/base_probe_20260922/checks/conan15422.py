"""Conan15422 行为裁决（behavior_check.sh 版；等价于已执行的 conan_fp_check.sh，另加 version / cmakeMinimumRequired 字段——
Qwen3.6 a2 把它们改成 4 / 3.25，参考测试不守护）。每行 RESULT= 一个 JSON。"""
import json
import os

from conans.test.assets.genconanfile import GenConanfile
from conans.test.utils.tools import TestClient

os.environ.setdefault("CONAN_HOME", "/tmp/ch")
for label, extra, basis in [
    ("no_conf", "", "gold：未配置时写 build_jobs()（容器 CPU 配额）；公开 helper 语义可推出默认；F2P 不覆盖"),
    ("jobs42_single", " -c tools.build:jobs=42", "唯一 F2P 的路径：显式 42"),
    ("jobs42_ninja_multi", " -c tools.build:jobs=42 -c tools.cmake.cmaketoolchain:generator=\"Ninja Multi-Config\"", "gold：多配置同样写 42；F2P 不覆盖"),
    ("jobs10_msvc_vs2022", " -s os=Windows -s arch=x86_64 -s compiler=msvc -s compiler.version=193 -s compiler.runtime=dynamic -c tools.build:jobs=10",
     "DeepSeek a4 给生成器加门（VS / Xcode / NMake 不写 jobs）；gold 写 10；题卡记生成器范围未唯一规定——待裁决"),
]:
    c = TestClient()
    c.save({"conanfile.py": GenConanfile().with_settings("os", "arch", "compiler", "build_type").with_generator("CMakeToolchain")})
    try:
        c.run("install . -s build_type=Release" + extra)
    except Exception as exc:  # noqa: BLE001 - 某些 profile 组合在此 base 上可能不被接受，如实记录
        print("RESULT=" + json.dumps({"case": f"{label}__install_error", "value": f"{type(exc).__name__}: {str(exc)[:200]}", "basis": basis}, ensure_ascii=False))
        continue
    p = json.loads(c.load("CMakePresets.json"))
    print("RESULT=" + json.dumps({"case": f"{label}__build_presets_jobs", "value": [(bp.get("name"), bp.get("jobs")) for bp in p.get("buildPresets", [])], "basis": basis}, ensure_ascii=False))
    print("RESULT=" + json.dumps({"case": f"{label}__schema", "value": {"version": p.get("version"), "cmakeMinimumRequired": p.get("cmakeMinimumRequired")},
                                  "basis": "base 与 gold：version 3、cmakeMinimumRequired 3.15；源码声明预设面向 CMake ≥ 3.23；参考测试不守护"}, ensure_ascii=False))
