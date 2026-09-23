from probe_bootstrap import *
from miles.ray.rollout.train_data_conversion import convert_samples_to_train_data,split_train_data_by_dp_scheduled_raw
from miles.utils.types import Sample
from miles.utils.sampling_mask import RolloutSamplingMask
import itertools
args=Namespace(advantage_estimator='grpo',rewards_normalization=True,grpo_std_normalization=True,n_samples_per_prompt=8,rollout_batch_size=2,use_dynamic_global_batch_size=False,rollout_top_p=.9,reward_key=None,global_batch_size=8,use_dynamic_batch_size=True,max_tokens_per_gpu=32,balance_data=True,balance_by_flops=False,allow_partial_train_step=False)
samples=[]
for gi in [4,5]:
 for slot in range(8):
  rid=gi*8+slot
  for leaf in range(1+slot%3):
   resp=[3+slot%4]*(2+leaf);mask=[1]*(1+leaf)+[0];tokens=[1,2]+resp
   sample=Sample(group_index=gi,index=rid,rollout_id=rid,tokens=tokens,response_length=len(resp),loss_mask=mask,rollout_log_probs=[-.5 if x else 0. for x in mask],reward=float(slot>=gi-1),status=Sample.Status.COMPLETED,weight_versions=['11'],rollout_sampling_mask=RolloutSamplingMask(ids=list(itertools.chain.from_iterable([[x,8] if m else [x] for x,m in zip(resp,mask)])),offsets=[0]+list(itertools.accumulate([2 if m else 1 for m in mask]))))
   samples.append(sample)
data=convert_samples_to_train_data(args,samples,{},None,None)
for gi in [4,5]:
 rr=[float(slot>=gi-1) for slot in range(8)]; mean=sum(rr)/8;std=(sum((x-mean)**2 for x in rr)/7)**.5
 for i,s in enumerate(samples):
  if s.group_index==gi:assert abs(data['rewards'][i]-(s.reward-mean)/(std+1e-6))<1e-6
for i,s in enumerate(samples):
 expect=sum(sum(t.loss_mask) for t in samples if t.index==s.index)
 assert data['rollout_mask_sums'][i]==expect
shards=split_train_data_by_dp_scheduled_raw(args,data,train_parallel_config=dict(dp_size=2,cp_size=1,vpp_size=1,microbatch_group_size_per_vp_stage=1))
seen={}
for rank,sh in enumerate(shards):
 off=0
 for step,count in enumerate(sh['num_microbatches']):
  for batch in sh['micro_batch_indices'][off:off+count]:
   for pos in batch:
    rid=sh['rollout_ids'][pos];seen.setdefault(rid,set()).add(step)
  off+=count
assert len(seen)==16 and all(len(v)==1 for v in seen.values())
print(dict(executions=len(seen),leaves=len(samples),expected_execution_denominators=sorted(set(data['rollout_mask_sums'])),num_rollouts=shards[0]['num_rollouts'],num_microbatches=shards[0]['num_microbatches'],same_execution_same_optimizer_step=True,oracle='按8个成员独立计算均值/样本标准差;按原始leaf mask求execution分母'))
