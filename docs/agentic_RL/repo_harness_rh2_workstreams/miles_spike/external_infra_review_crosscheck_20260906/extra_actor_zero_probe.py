"""真实 CPU loss 与生产控制流探针；引擎和模型用替身，不证明 GPU 行为。"""
import ast,copy,importlib.util,sys,json,contextlib
from pathlib import Path
from argparse import Namespace
R=next(p for p in Path(__file__).resolve().parents if (p/'rh2/pyproject.toml').is_file());sys.path[:0]=[str(R/'rh2/src'),str(R/'reference/miles-rh2-integration')]
s=importlib.util.spec_from_file_location('rh2cf',R/'rh2/tests/adapters_miles/conftest.py');cf=importlib.util.module_from_spec(s);s.loader.exec_module(cf);cf._install_ray_stub()
import torch
from miles.backends.training_utils.parallel import ParallelState,set_parallel_state
from miles.utils.ft_utils.process_group_utils import GroupInfo
from miles.backends.training_utils.loss import compute_advantages_and_returns,loss_function
from repoharness2.adapters.miles import faithful_dis_loss as fd
fd._cp_all_reduce_sum=lambda t,cp:t
T=GroupInfo(rank=0,size=1,group=None)
set_parallel_state(ParallelState(intra_dp=T,intra_dp_cp=T,cp=T,tp=T,pp=T,ep=T,etp=T,indep_dp=T,is_pp_last_stage=True))
a=Namespace(qkv_format='thd',rollout_temperature=1.,true_on_policy_mode=True,log_probs_chunk_size=-1,allgather_cp=False,rollout_top_p=.9,rollout_top_k=2,vocab_size=2,bf16=False,fp16=False,calculate_per_token_loss=False,loss_type='custom_loss',custom_loss_function_path='repoharness2.adapters.miles.faithful_dis_loss.faithful_dis_loss_function',recompute_loss_function=False,use_dynamic_global_batch_size=False,global_batch_size=16,skip_actor_forward_only=False,use_rollout_logprobs=False,kl_coef=0.,use_opd=False,normalize_advantages=False,advantage_estimator='grpo')
# 两组n8: 环境1奖励token0，环境2奖励token1；模型暂时忽略prompt，两个任务梯度相反。
y=[0]*4+[1]*4+[0]*4+[1]*4
rewards=[1.]*4+[-1.]*4+[-1.]*4+[1.]*4
base=dict(tokens=torch.tensor([[t for v in y for t in [0,v]]]),unconcat_tokens=[torch.tensor([0,v]) for v in y],total_lengths=[2]*16,response_lengths=[1]*16,loss_masks=[torch.ones(1) for _ in y],rollout_mask_sums=torch.ones(16),rewards=rewards,rollout_log_probs=[torch.tensor([-.6931471805599453],dtype=torch.float64) for _ in y],rollout_sampling_mask_ids=[[0,1] for _ in y],rollout_sampling_mask_offsets=[[0,2] for _ in y])
runs=[]
for use_rollout in [False,True]:
 a.use_rollout_logprobs=use_rollout;b=copy.deepcopy(base)
 if not use_rollout:b['log_probs']=[torch.tensor([-12.0]) for _ in y] # 故意与行为值不同，确认只消费形状。
 compute_advantages_and_returns(a,b)
 theta=torch.zeros(2,dtype=torch.float64,requires_grad=True);logits=theta[None,None,:].expand(1,32,2)
 loss,_,metrics=loss_function(a,b,1,logits,True,16);loss.backward()
 runs.append(dict(use_rollout_logprobs=use_rollout,loss=float(loss.detach()),gradient=theta.grad.tolist(),advantages=[float(v[0]) for v in b['advantages']],metrics=dict(zip(metrics['keys'],metrics['values'].tolist()[1:]))))
assert runs[0]['loss']==runs[1]['loss'] and runs[0]['gradient']==runs[1]['gradient']
assert runs[0]['gradient']==[0.,0.]
assert all(r['metrics']['dis_accepted_tokens']==16 and all(abs(v)==1 for v in r['advantages']) for r in runs)
# 再用同向奖励检验非零梯度，避免等价性只在抵消例上通过。
nonzero_runs=[]
for use_rollout in [False,True]:
 a.use_rollout_logprobs=use_rollout;b=copy.deepcopy(base);b['rewards']=[1.]*4+[-1.]*4+[1.]*4+[-1.]*4
 if not use_rollout:b['log_probs']=[torch.tensor([-12.0]) for _ in y]
 compute_advantages_and_returns(a,b)
 theta=torch.zeros(2,dtype=torch.float64,requires_grad=True);logits=theta[None,None,:].expand(1,32,2)
 loss,_,metrics=loss_function(a,b,1,logits,True,16);loss.backward()
 nonzero_runs.append(dict(use_rollout_logprobs=use_rollout,loss=float(loss.detach()),gradient=theta.grad.tolist(),advantages=[float(v[0]) for v in b['advantages']]))
assert nonzero_runs[0]['loss']==nonzero_runs[1]['loss']
assert nonzero_runs[0]['gradient']==nonzero_runs[1]['gradient']
assert any(v!=0 for v in nonzero_runs[0]['gradient'])
# AST提取整段生产train_actor（去decorator以免Ray/Megatron初始化），仅环境/model kernel替身。
source=R/'reference/miles-rh2-integration/miles/backends/megatron_utils/actor.py'
tree=ast.parse(source.read_text());f=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='train_actor');f.decorator_list=[]
module=ast.fix_missing_locations(ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),f],type_ignores=[]))
class Outcome: NORMAL='normal'
class Event:
 def __init__(self):self.events=[]
 def enabled(self):return True
 def emit(self,event,**kw):self.events.append(event)
class Replay:
 enabled=True; name='routing';data_key='routed_experts';replays=[];register_replay_list_func=None;if_sp_region=None;replay_indices_are_token_positions=False
 def __init__(self):self.stage='init';self.calls=[]
 def consumption_snapshot(self):return dict(num_streams=1,queue_lens=[1],forward_indices=[1],backward_indices=[1])
 def clear_all_forward(self):self.calls.append('clear_forward')
 def clear_all(self):self.calls.append('clear_all')
class Actor:
 def __init__(self,a,m):
  self.args=a;self.model=[];self.weights_backuper=Namespace(backup_tags=[]);self._active_model_tag='actor';self.rollout_data_postprocess=None;self.optimizer=None;self.opt_param_scheduler=None;self._ft_test_action_executor=None;self.prof=Namespace(step=lambda **kw:None);self._enable_weight_backup=False;self.weight_updater=Namespace(weight_version=3,pop_metrics=lambda:{});self._heartbeat=Namespace(bump=lambda:None);self.calls=[];self.m=m
 def _use_rollout_replay(self,m):return True
 def _switch_model(self,tag):self._active_model_tag=tag
 def _set_replay_stage(self,stage):self.m.stage=stage
 def compute_log_prob(self,*args,**kw):self.calls.append(('compute_log_prob',self.m.stage));return dict(log_probs=[torch.tensor([-12.]) for _ in y])
 def _emit_logprob_compare(self,*args):self.calls.append(('logprob_compare',self.m.stage))
actors=[]
for use_rollout,mismatch in [(False,False),(True,False),(True,True)]:
 a.use_rollout_logprobs=use_rollout;a.get_mismatch_metrics=mismatch;a.compute_advantages_and_returns=True;a.keep_old_actor=False;a.use_critic=False;a.ref_update_interval=None
 m=Replay();e=Event();actor=Actor(a,m);b=copy.deepcopy(base);b['routed_experts']=['tape']
 def fill(**kw):actor.calls.append(('fill',m.stage));del kw['rollout_data']['routed_experts']
 def train(*args,**kw):actor.calls.append(('train',m.stage));return 'zero_signal_skipped' # 不走GPU synchronize；只验证进入训练时的数据和阶段。
 ns=dict(rh2_event_log=e,dist=Namespace(get_rank=lambda:0,is_initialized=lambda:False),get_data_iterator=lambda *x:(['iterator'],[1]),all_replay_managers=[m],replay_sample_digests=lambda *x:['hash'],fill_replay_data=fill,get_parallel_state=lambda:Namespace(effective_dp=T,is_pp_last_stage=True),inverse_timer=lambda *x:contextlib.nullcontext(),timer=lambda *x:contextlib.nullcontext(),compute_advantages_and_returns=compute_advantages_and_returns,log_train_advantage_computation_event=lambda *x:None,log_rollout_data=lambda *x:None,get_num_rollouts=lambda *x:16,train=train,train_dump_utils=Namespace(save_debug_train_data=lambda *x,**kw:None),TrainStepOutcome=Outcome,is_multi_lora_enabled=lambda *x:False,log_perf_data=lambda *x,**kw:None)
 exec(compile(module,str(source),'exec'),ns);ns['train_actor'](actor,0,b,witness_info=None,attempt=0)
 assert sum(name=='compute_log_prob' for name,_ in actor.calls)==int(not use_rollout or mismatch)
 assert sum(name=='logprob_compare' for name,_ in actor.calls)==int(not use_rollout or mismatch)
 assert ('train','replay_backward') in actor.calls
 actors.append(dict(use_rollout_logprobs=use_rollout,get_mismatch_metrics=mismatch,calls=actor.calls,replay_calls=m.calls,events=e.events,advantages=[float(v[0]) for v in b['advantages']]))
result=dict(real_advantage_and_custom_loss=runs,nonzero_gradient_flag_comparison=nonzero_runs,production_train_actor_ast_with_environment_stubs=actors)
print(json.dumps(result,indent=2))
