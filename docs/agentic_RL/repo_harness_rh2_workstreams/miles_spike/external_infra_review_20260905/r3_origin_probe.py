from probe_bootstrap import *
from slime.agent.trajectory import TrajectoryManager,TurnRecord,_SampleBuilder,DriftKind
from slime.utils.types import Sample
from repoharness2.adapters.slime.generate import backfill_leaf_sample,TurnTape,TurnIdentitySpan
u={'role':'user','content':'task'};aa={'role':'assistant','content':'first'};tool={'role':'user','content':'tool result'};ab={'role':'assistant','content':'second'}
t1=TurnRecord(prompt_ids=[1,2],output_ids=[3,4],finish_reason='stop',output_log_probs=[-.1,-.2]);t2=TurnRecord(prompt_ids=[1,2,3,4,5],output_ids=[6,7],finish_reason='stop',output_log_probs=[-.3,-.4])
m=TrajectoryManager(fork_threshold_tokens=0);m.record_turn('s',turn=t1,prompt_messages=[u],response_message=aa);m.record_turn('s',turn=t2,prompt_messages=[u,aa,tool],response_message=ab)
[s]=m.get_trajectory('s',base_sample=Sample(index=0,group_index=0))
assert s.tokens==t2.prompt_ids+t2.output_ids
first=TurnTape('a',1,2,2,(3,4),(-.1,-.2),None,None,(1,1,1),'10');last=TurnTape('b',2,5,2,(6,7),(-.3,-.4),None,None,(7,7,7,7,7,7),'11')
backfill_leaf_sample(s,[first,last],moe_num_layers=1,moe_router_topk=1,require_real_weight_versions=True,identity_spans=[TurnIdentitySpan(0,2,'a'),TurnIdentitySpan(3,2,'b')])
print(dict(real_manager_tokens=s.tokens,loss_mask=s.loss_mask,behavior_logprobs=s.rollout_log_probs,original_first_turn_decode_routes=list(first.routed_experts_flat)[1:],final_first_turn_response_routes=s.rollout_routed_experts[1:3],weight_versions=s.weight_versions,scope='真实TrajectoryManager→backfill;使用人工两轮tape证明选列;不证明真实GPU不同轮路由差异'))
# 独立穷举三种builder转换；不修改vendor或使用项目测试oracle。
for prompt,output,kind in [([1,2],[3,4],DriftKind.CLEAN),([1,2,3,4,5],[6],DriftKind.CLEAN),([1,2,3,4,5,9],[7],DriftKind.REALIGN)]:
 if prompt==[1,2]:b=_SampleBuilder(100)
 turn=TurnRecord(prompt_ids=prompt,output_ids=output,finish_reason='stop')
 assert b.classify_token_drift(turn)==kind
 b.append_turn(turn,kind)
 assert b.tokens==prompt+output
print('真实builder CLEAN/REALIGN 三步均保持 tokens=当前prompt+output；FORK以新builder同构。因此未复现中间token裁剪错位。')
