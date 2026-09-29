from pathlib import Path
import hashlib,json,re,sys
R=Path('runs/category2_repair_20260929/swe_materials')
D=Path('docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/swe_materials')
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
errors=[];checks=[]
def check(ok,msg):
 checks.append({'check':msg,'passed':bool(ok)})
 if not ok:errors.append(msg)
inv=read(D/'swe_inventory.json');start=read(D.parent/'starting_inventory.json');wanted={t['instance_id'] for t in start['tasks'] if t['source']=='SWE'}
check(len(inv['tasks'])==28 and {t['instance_id'] for t in inv['tasks']}==wanted,'28题与固定SWE第2类名单精确一致')
packids=[t for p in inv['packs'] for t in p['instance_ids']]
check(len(packids)==len(set(packids))==28 and set(packids)==wanted,'12小包无遗漏或重复且不含第3类')
for t in inv['tasks']:
 for src in t['material_entries']:check(Path(src['path']).is_file() and sha(src['path'])==src['sha256'],'清单源SHA:'+src['path'])
manifest=read(D/'first_mypy_bundle/materials_manifest.json')
for t in manifest['tasks']:
 nodes=t['required_collected_node_ids']; check(len(nodes)==len(set(nodes))==t['expected_reference_count'],'唯一预期节点:'+t['instance_id'])
 check(nodes==t['revised_fail_to_pass']+t['revised_pass_to_pass'],'引用与选择节点集合:'+t['instance_id'])
 check(t['public_revision'] is None and t['test_patch_revision'] is None,'不改题面和原test.patch:'+t['instance_id'])
 for v in t['frozen_assets'].values():
  check(sha(v['source']['path'])==v['source']['sha256']==sha(v['frozen']['path'])==v['frozen']['sha256'],'冻结候选/材料逐字相同:'+v['frozen']['path'])
 for c in t['additional_p2p']:
  lines=Path(c['source']['path']).read_text().splitlines(keepends=True);body=''.join(lines[c['start_line']-1:c['end_line']])
  check(hashlib.sha256(body.encode()).hexdigest()==c['case_bytes_sha256'],'原公开case字节:'+c['case'])
  check('FAILED '+c['node_id'] in Path(c['node_id_observed_in_historical_real_pytest']['path']).read_text(),'历史真实节点证据:'+c['node_id'])
 check(t['restore_requirement']['additional_trusted_public_file'] not in Path(t['unchanged_test_patch']['path']).read_text(),'新增可信恢复文件确未被原patch覆盖:'+t['instance_id'])
 check(len(t['install_proposal']['required_wheels'])==len(t['install_proposal']['wheel_pins']),'全部所需wheel已绑定SHA:'+t['instance_id'])
for src in read(R/'first_mypy_bundle/source_receipts.json')['files']:
 check(Path(src['path']).is_file() and sha(src['path'])==src['sha256'],'首包源SHA:'+src['path'])
for p in D.rglob('*.md'):
 for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if not link.startswith(('https:','http:','#')):
   check((p.parent/link.split('#')[0]).is_file(),'Markdown本地链接:'+str(p)+':'+link)
report={'status':'passed' if not errors else 'failed','scope':'本地材料、源SHA、冻结字节、已观察节点/范围/链接的一致性；未执行mypy/pytest/安装/容器/SSH/模型，非独立运行验收','checks_total':len(checks),'failed':errors,'checks':checks}
(R/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['status','checks_total','failed','scope']},ensure_ascii=False))
sys.exit(bool(errors))
