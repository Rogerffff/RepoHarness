"""交叉审查：accepted token 不能证明非零梯度；只调用真实CPU loss。"""
import sys
from pathlib import Path
repo = next(p for p in Path(__file__).resolve().parents if (p/'rh2/pyproject.toml').is_file())
sys.path.insert(0,str(repo/'docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/external_infra_review_20260905'))
from probe_bootstrap import *
state(1,0)
a.qkv_format='thd'; a.global_batch_size=1
logits=torch.randn((1,3,9),dtype=torch.float64,requires_grad=True)
tokens=torch.tensor([[0,2,3]])
batch=dict(tokens=tokens,unconcat_tokens=[tokens[0]],total_lengths=[3],response_lengths=[2],loss_masks=[torch.tensor([1,1])],rollout_mask_sums=torch.tensor([2]),advantages=[torch.tensor([1.,1.],dtype=torch.float64)],rollout_log_probs=[torch.tensor([0.,0.],dtype=torch.float64)],rollout_sampling_mask_ids=[[2,3]],rollout_sampling_mask_offsets=[[0,1,2]])
loss,_,metrics=loss_function(a,batch,1,logits,True,1)
loss.backward()
metric_values=dict(zip(metrics['keys'],metrics['values'][1:].tolist()))
print({'loss':float(loss.detach()),'max_abs_logit_grad':float(logits.grad.abs().max()),'metrics':metric_values})
assert metric_values['dis_accepted_tokens']==2
assert float(loss.detach())==0 and float(logits.grad.abs().max())==0
