# 公开开发检查（来源：quality_batch01 cpu_queue.json 的 actor-conan15422 command_draft；只含公开内容）。
# 每步独立记录退出码；base 上 "jobs" 断言失败是目标功能缺失，不是环境错误。
step() { echo "=== STEP $1"; shift; "$@"; echo "=== RC $?"; }
step import python -c 'import sys, conan, conans; from conan.tools.cmake import presets; print(sys.executable, sys.version); print(conan.__file__, conans.__file__, presets.__file__)'
step presets_jobs2 python - <<'PYCODE'
import json
from conans.test.assets.genconanfile import GenConanfile
from conans.test.utils.tools import TestClient
c = TestClient()
c.save({'conanfile.py': GenConanfile().with_settings('os', 'arch', 'compiler', 'build_type').with_generator('CMakeToolchain')})
c.run('install . -s build_type=RelWithDebInfo -c tools.cmake.cmaketoolchain:generator="Unix Makefiles" -c tools.build:jobs=2')
p = json.loads(c.load('CMakePresets.json'))['buildPresets'][0]
print(p)
assert p['name'] == 'conan-relwithdebinfo'
assert p['configurePreset'] == 'conan-relwithdebinfo'
assert type(p.get('jobs')) is int and p['jobs'] == 2, p
PYCODE
step narrow_tests_1 python -m pytest -q conans/test/unittests/tools/cmake/test_cmake_cmd_line_args.py conans/test/integration/tools/cpu_count_test.py
step narrow_tests_2 python -m pytest -q conans/test/integration/toolchains/cmake/test_cmaketoolchain.py -k "test_cmake_presets_singleconfig or test_cmake_presets_multiconfig"
step git_status git status --porcelain
