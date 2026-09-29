"""建立仅修Moto日志去向的环境版本；保留题目代码、完整测试和参考集合。"""

import json
from pathlib import Path
import shutil

ROOT = Path('/work/env_recipe_repair_20260919')
DEST = ROOT/'modin_s3_compat_v3'
ROUTE = r'''
python -I - <<'RH2_MOTO_FILE_LOG' || exit $?
from pathlib import Path
import hashlib, json, shlex, sys
p = Path(sys.executable).parent / 'moto_server'
original = p.with_name('moto_server.rh2-original')
assert p.is_file() and not original.exists()
before = hashlib.sha256(p.read_bytes()).hexdigest()
p.rename(original)
p.write_text('#!/bin/sh\nexec ' + shlex.quote(str(original)) + ' "$@" 2>>/tmp/rh2-moto-server.log\n')
p.chmod(0o755)
print('RH2_MOTO_LOG_ROUTE=' + json.dumps({'original_sha256': before, 'wrapper_sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'log': '/tmp/rh2-moto-server.log'}))
RH2_MOTO_FILE_LOG
'''
OBSERVE = r'''
python -I - <<'RH2_MOTO_LOG_OBSERVE'
from pathlib import Path
import hashlib, json
p = Path('/tmp/rh2-moto-server.log')
if p.is_file():
    data = p.read_bytes()
    print('RH2_OBS_MOTO_LOG=' + json.dumps({'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'tail':data[-12000:].decode(errors='replace'),'diagnostic_only':True}))
else:
    print('RH2_OBS_MOTO_LOG=missing')
RH2_MOTO_LOG_OBSERVE
'''


def main():
    proof = json.loads((ROOT/'moto_log_backpressure_probe_v5/result.json').read_text())
    original, corrected = proof['result']['results']
    assert original['recovered_after_log_drain'] and corrected['actual_object_roundtrip']
    assert corrected['completed_requests'] == 4096 and proof['container_removed']
    DEST.mkdir(exist_ok=False)
    (DEST/'recipes').mkdir()
    plans = json.loads((ROOT/'modin_s3_compat_v2/plan.json').read_text())
    for item in plans:
        item['environment']['RH2_GRADER_PIDS_LIMIT'] = '512'
        item['grading_label_prefix'] = 'rh2.envrepair.modin_s3_compat_v3'
        item['wait_for_superseded_batches'] = ['modin_s3_compat_v2']
        has_pipe = item['instance_id'].endswith('-6937')
        item['reason'] = ('Unconsumed stderr pipe blocked Moto request logging; redirect service stderr to candidate-owned file, retain original tests/refs; restore PID512 to verify root cause instead of increasing capacity.'
                          if has_pipe else 'Original5940 fixture uses DEVNULL, not PIPE; no logging override. Complete previously queued Moto4 compatibility control at original PID512, full source tests/refs unchanged.')
        recipe = json.loads((ROOT/'modin_s3_compat_v2/recipes'/(item['instance_id']+'.json')).read_text())
        if has_pipe:
            # 确保路由发生在固定版本安装之后、原候选源码安装之前。
            assert recipe['revised_install'].endswith(recipe['original_install'])
            install = recipe['revised_install'][:-len(recipe['original_install'])]
            recipe['revised_install'] = install + ROUTE + '\n' + recipe['original_install']
            recipe['post_observation_append'] = OBSERVE
        recipe['decision'] = 'E26'
        recipe['reason'] = item['reason']
        (DEST/'recipes'/(item['instance_id']+'.json')).write_text(json.dumps(recipe,indent=2)+'\n')
    (DEST/'plan.json').write_text(json.dumps(plans,indent=2)+'\n')
    for name in ['run_compat_cases.py','replay_with_install_recipe.py']:
        shutil.copyfile(ROOT/(name+'.next_v3'),DEST/name)
    shutil.copyfile(Path(__file__),DEST/'prepare_moto_file_log_cases.py')
    print(json.dumps({'prepared':str(DEST),'scope':'same source tests/refs, bounded PID512; not yet graded'}))


if __name__ == '__main__':
    main()
