"""在Ray启动前配置来源的模拟S3凭据；保持完整测试、断言与参考集合。"""

import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path('/work/env_recipe_repair_20260919')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-batch', default='modin_s3_compat_v3')
    parser.add_argument('--dest-batch', default='modin_s3_compat_v5')
    parser.add_argument('--instance-id', default='modin-project__modin-5940')
    args = parser.parse_args()
    source = ROOT/args.source_batch
    DEST = ROOT/args.dest_batch
    IID = args.instance_id
    DEST.mkdir(exist_ok=False)
    (DEST/'recipes').mkdir()
    item = next(x for x in json.loads((source/'plan.json').read_text()) if x['instance_id'] == IID)
    recipe = json.loads((source/'recipes'/(IID+'.json')).read_text())
    # 这两个字面量来自Modin自身的CIAWS*默认值，是本地Moto的假凭据。
    # 不设MODIN_GITHUB_CI：它还会改变S3地址和其它CI行为。
    exports = (
        'export AWS_ACCESS_KEY_ID=foobar_key\n'
        'export AWS_SECRET_ACCESS_KEY=foobar_secret\n'
        "printf '%s\\n' 'RH2_MOCK_S3_CREDENTIALS=source_defaults_before_ray'\n"
    )
    assert 'AWS_ACCESS_KEY_ID' not in recipe['revised_install']
    recipe['revised_install'] = exports + recipe['revised_install']
    recipe['decision'] = 'E28'
    recipe['reason'] = (
        'Local S3 operations fail with RayTaskError(NoCredentialsError). '
        's3_base sets source dummy credentials after Ray workers start; '
        'initialize_ray only propagates them explicitly when GithubCI is true. '
        'Export the exact source dummy defaults before pytest/Ray start, '
        'without enabling CI or changing endpoints, source tests or references. '
        'Public asset failures remain held under E23.'
    )
    item.pop('wait_for_superseded_batches', None)
    item['wait_for_batches'] = [args.source_batch]
    item['grading_label_prefix'] = 'rh2.envrepair.'+args.dest_batch
    item['reason'] = recipe['reason']
    item['reuse_prepared_image'] = args.source_batch+'/tasks/'+IID+'/image.json'
    prepared = json.loads((ROOT/item['reuse_prepared_image']).read_text())
    item['image'] = item['image_id'] = prepared['image_id']
    (DEST/'recipes'/(IID+'.json')).write_text(json.dumps(recipe,indent=2)+'\n')
    (DEST/'plan.json').write_text(json.dumps([item],indent=2)+'\n')
    (DEST/'credential_revision.json').write_text(json.dumps({
        'version': IID+'-mock-credentials-v1', 'decision': 'E28', 'instance_id': IID,
        'parent_batch': args.source_batch,
        'source_config': 'modin/config/envvars.py:CIAWSAccessKeyID,CIAWSSecretAccessKey',
        'source_ray': 'modin/core/execution/ray/common/utils.py:initialize_ray',
        'source_fixture': 'modin/conftest.py:s3_base',
        'source_evidence': ('source5940_ray_config_2140.json; source5940_s3_inspection_2137.json'
                            if IID.endswith('5940') else 'source6937_access_helpers_2228.json; modin_s3_compat_v4/analysis_1.json'),
        'change': 'export source dummy credentials before Ray initialization',
        'scope': 'diagnostic environment recipe; same Moto4, resource policy, tests, references, network=none',
        'not_changed_from_parent': ['GithubCI', 'endpoints', 'test fixtures', 'assertions', 'public source material hold'],
    },indent=2)+'\n')
    for name in ['run_compat_cases.py','replay_with_install_recipe.py']:
        shutil.copyfile(source/name,DEST/name)
    shutil.copyfile(Path(__file__),DEST/'prepare_modin_mock_credentials.py')
    subprocess.run(['bash','-n'],input=recipe['revised_install'],text=True,check=True)
    print(json.dumps({'prepared':str(DEST),'state':'awaiting_complete_original_pair'}))


if __name__ == '__main__':
    main()
