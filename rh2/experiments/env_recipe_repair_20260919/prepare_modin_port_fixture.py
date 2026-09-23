"""版本化6937的S3 fixture端口修订；不改变测试命令、断言与参考集合。"""

import ast
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path('/work/env_recipe_repair_20260919')
DEST = ROOT/'modin_s3_compat_v4'
IID = 'modin-project__modin-6937'


def main():
    DEST.mkdir(exist_ok=False)
    (DEST/'recipes').mkdir()
    item = json.loads((ROOT/'modin_s3_compat_v3/plan.json').read_text())[0]
    assert item['instance_id'] == IID
    name = 'rh2-er19-port-fixture-read'
    try:
        result = subprocess.run([
            'docker','run','--rm','--name',name,'--network','none','--memory','128m','--cpus','1',
            '--pids-limit','32','--entrypoint','/bin/cat',item['image_id'],'/testbed/modin/conftest.py',
        ],capture_output=True,text=True,timeout=60,check=True)
        before = result.stdout
    finally:
        subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=30)
        assert not subprocess.check_output(['docker','ps','-aq','--filter','name=^/'+name+'$'],text=True).strip()
    old = ('        worker_id = "5" if worker_id == "master" else worker_id.lstrip("gw")\n'
           '        url = f"http://127.0.0.1:555{worker_id}/"')
    new = ('        endpoint_port = 5500 if worker_id == "master" else 5550 + int(worker_id.lstrip("gw"))\n'
           '        url = f"http://127.0.0.1:{endpoint_port}/"')
    assert before.count(old) == 1
    after = before.replace(old,new,1)
    # 清除同一个fixture中的过时注释，实际s3_base函数及其它定义保持不变。
    comment = ('        # to. We arbitrarily assign `5` as a worker id to the master worker, since we need a number\n'
               '        # for each worker, and we never run tests with more than `pytest -n 4`.')
    assert after.count(comment) == 1
    after = after.replace(comment,'        # to. Match the endpoint_port calculation in s3_base, including the master worker.',1)
    before_tree, after_tree = ast.parse(before), ast.parse(after)
    old_nodes, new_nodes = before_tree.body, after_tree.body
    assert len(old_nodes) == len(new_nodes)
    changes = [(a,b) for a,b in zip(old_nodes,new_nodes) if ast.dump(a) != ast.dump(b)]
    assert len(changes) == 1 and changes[0][0].name == changes[0][1].name == 's3_storage_options'
    old_asserts = [ast.dump(n) for n in ast.walk(before_tree) if isinstance(n,ast.Assert)]
    assert old_asserts == [ast.dump(n) for n in ast.walk(after_tree) if isinstance(n,ast.Assert)]
    before_sha = hashlib.sha256(before.encode()).hexdigest()
    after_sha = hashlib.sha256(after.encode()).hexdigest()
    (DEST/'conftest.before.py').write_text(before)
    (DEST/'conftest.after.py').write_text(after)
    (DEST/'fixture.patch').write_text(''.join(difflib.unified_diff(
        before.splitlines(keepends=True),after.splitlines(keepends=True),
        fromfile='a/modin/conftest.py',tofile='b/modin/conftest.py')))
    setup = (
        "python -I - <<'RH2_PORT_FIXTURE'\n"
        "from pathlib import Path\nimport hashlib, json\n"
        "p=Path('/testbed/modin/conftest.py')\n"
        f"assert hashlib.sha256(p.read_bytes()).hexdigest()=={before_sha!r}\n"
        f"p.write_text({after!r})\n"
        f"assert hashlib.sha256(p.read_bytes()).hexdigest()=={after_sha!r}\n"
        "print('RH2_PORT_FIXTURE=' + json.dumps({'version':'modin6937-port-v1','sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))\n"
        "RH2_PORT_FIXTURE\n"
    )
    recipe = json.loads((ROOT/'modin_s3_compat_v3/recipes'/(IID+'.json')).read_text())
    assert 'trusted_setup_append' not in recipe
    recipe.update(trusted_setup_append=setup,decision='E27',
                  reason='Versioned source fixture endpoint repair: s3_storage_options master5555 differs from s3_base master5500. Match its calculation; no original assertions/test command/ref changes. Preserve log route E26.')
    (DEST/'recipes'/(IID+'.json')).write_text(json.dumps(recipe,indent=2)+'\n')
    item.pop('wait_for_superseded_batches',None)
    item['wait_for_batches']=['modin_s3_compat_v3']
    item['grading_label_prefix']='rh2.envrepair.modin_s3_compat_v4'
    item['reason']=recipe['reason']
    item['reuse_prepared_image']='modin_s3_compat_v3/tasks/'+IID+'/image.json'
    (DEST/'plan.json').write_text(json.dumps([item],indent=2)+'\n')
    evidence = {
        'version':'modin6937-port-v1','decision':'E27','instance_id':IID,
        'base_image_id':item['image_id'],'path':'modin/conftest.py',
        'before_sha256':before_sha,'after_sha256':after_sha,
        'only_changed_ast_node':'s3_storage_options','existing_asserts_preserved':len(old_asserts),
        'scope':'diagnostic trusted setup input; source test_patch, command and references unchanged; refreeze versioned fixture before production',
        '5940':'unchanged: its original producer and consumer both use5555 for master',
    }
    (DEST/'fixture_revision.json').write_text(json.dumps(evidence,indent=2)+'\n')
    for name in ['run_compat_cases.py','replay_with_install_recipe.py']:
        shutil.copyfile(ROOT/'modin_s3_compat_v3'/name,DEST/name)
    shutil.copyfile(Path(__file__),DEST/'prepare_modin_port_fixture.py')
    subprocess.run(['bash','-n'],input=setup,text=True,check=True)
    print(json.dumps(evidence))


if __name__ == '__main__':
    main()
