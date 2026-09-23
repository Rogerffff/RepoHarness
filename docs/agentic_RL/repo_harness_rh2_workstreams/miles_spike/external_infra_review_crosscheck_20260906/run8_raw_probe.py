"""读取唯一留存 projection 与 capture 原始 token；不推断其余样本。"""
import json,struct,hashlib
from pathlib import Path
R=next(p for p in Path(__file__).resolve().parents if (p/'rh2/pyproject.toml').is_file())/'docs/agentic_RL/repo_harness_rh2_workstreams/s1/7a_artifacts/artifacts_run8'
allproj=list(R.glob('rollouts/*/trajectory_projection.json'));out=[]
for p in allproj:
 d=p.parent;caps=json.loads((d/'capture_records.json').read_text());proj=json.loads(p.read_text());ids=[]
 for c in caps:
  row=[]
  for key in ['prompt_token_ids_ref','response_token_ids_ref']:
   ref=c[key];raw=(d/'tapes'/f"{ref['ref_id']}.bin").read_bytes();assert hashlib.sha256(raw).hexdigest()==ref['sha256'].split(':')[1];row.append(list(struct.unpack('<'+'i'*(len(raw)//4),raw)))
  ids.append(row)
 prefix=ids[0][0]+ids[0][1];nxt=ids[1][0];common=next((i for i,(a,b) in enumerate(zip(prefix,nxt)) if a!=b),min(len(prefix),len(nxt)))
 out.append(dict(projection=str(p.relative_to(R)),model=caps[0]['model_name'],captures=len(caps),t0_tokens=len(ids[0][1]),t1_tokens=len(ids[1][1]),old_response_start=len(ids[0][0]),first_divergence=common,branch_capture_refs=[b['capture_record_refs'] for b in proj['branches']],old_response_first_ids=ids[0][1][:10],next_at_old_response_start=nxt[len(ids[0][0]):len(ids[0][0])+10]))
transport=json.loads((R/'transport_verify.json').read_text())
print(json.dumps(dict(retained_projections=len(allproj),transport_top_keys=list(transport),raw=out),indent=2))
assert len(out)==1 and out[0]['first_divergence']-out[0]['old_response_start']==556
assert out[0]['t0_tokens']==624 and all(not ref.endswith('_t0') for branch in out[0]['branch_capture_refs'] for ref in branch)
