import sys,json
sys.path.insert(0,'rh2/src')
from slime.agent.trajectory import TrajectoryManager,TurnRecord
from slime.agent.adapters.anthropic import AnthropicAdapter
from slime.utils.types import Sample
from repoharness2.adapters.slime.turn_identity import attach_turn_identity_spans
from repoharness2.adapters.slime.generate import backfill_leaf_sample,TurnTape,RH2_TURN_IDENTITY_SPANS_ATTR
p=[100,101];u={'role':'user','content':'task'};a={'role':'assistant','content':'original'};tool={'role':'tool','content':'observation'}
rows=[]
for case in ('clean','token_drift','message_rewrite'):
 for threshold in (1024,0):
  for n in ((20,1024) if case=='token_drift' else (20,)):
   m=TrajectoryManager(fork_threshold_tokens=threshold);r1=[201,202,203,204];r2=list(range(5000,5000+n))
   t1=TurnRecord(p,r1,'stop',[-.2]*len(r1));p2=p+r1+[300]
   if case=='token_drift':p2[4]=999
   echoed=dict(a)
   if case=='message_rewrite':echoed['content']='rewritten';p2[4]=999
   t2=TurnRecord(p2,r2,'stop',[-.3]*len(r2))
   m.record_turn('s',turn=t1,prompt_messages=[u],response_message=a)
   m.record_turn('s',turn=t2,prompt_messages=[u,echoed,tool],response_message={'role':'assistant','content':'done'})
   root=m._trees['s'];leaves=len(list(root.leaves()))
   samples=m.get_trajectory('s',base_sample=Sample(index=0,group_index=0,prompt='task'),reward=1)
   attach_turn_identity_spans(samples,root,fork_threshold=m._fork_threshold,resolve_capture_id=lambda i:f'c{i}')
   all_tapes={f'c{i}':TurnTape(f'c{i}',i,len(t.prompt_ids),len(t.output_ids),tuple(t.output_ids),tuple(t.output_log_probs),None,None,None,str(i)) for i,t in enumerate((t1,t2),1)}
   used=[]
   for s in samples:
    spans=getattr(s,RH2_TURN_IDENTITY_SPANS_ATTR)
    tapes=[all_tapes[x.capture_record_id] for x in spans]
    used.extend(t.record_id for t in backfill_leaf_sample(s,tapes,identity_spans=spans,require_real_weight_versions=True))
   row={'case':case,'threshold':threshold,'new_output':n,'tree_leaves':leaves,'samples':len(samples),'trained_tokens':sum(sum(s.loss_mask) for s in samples),'used_capture_ids':used,'rewards':[s.reward for s in samples]}
   assert row['trained_tokens']==(4+n if threshold==0 or case=='clean' or n>=1024 else n)
   assert used==(['c1','c2'] if row['trained_tokens']==4+n else ['c2'])
   rows.append(row)
print(json.dumps(rows,ensure_ascii=False,indent=2))
adapter=AnthropicAdapter(tokenizer=object(),sglang_url='http://unused',fork_threshold_tokens=0)
assert adapter.manager._fork_threshold==0
print('library_constructor_zero_override=PASS; identity_replay_and_backfill=PASS; cases=8')
