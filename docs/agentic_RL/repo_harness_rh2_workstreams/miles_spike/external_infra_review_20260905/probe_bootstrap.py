"""CPU 审查探针共用引导：模拟并行状态，不用于正式训练。"""
import sys, importlib.util, math, random
from pathlib import Path
from argparse import Namespace
R=next(p for p in Path(__file__).resolve().parents if (p/'rh2/pyproject.toml').is_file())
sys.path[:0]=[str(R/'rh2/src'),str(R/'reference/miles-rh2-integration')]
s=importlib.util.spec_from_file_location('rh2cf', R/'rh2/tests/adapters_miles/conftest.py'); cf=importlib.util.module_from_spec(s); s.loader.exec_module(cf); cf._install_ray_stub()
import torch
from miles.backends.training_utils.parallel import ParallelState,set_parallel_state
from miles.utils.ft_utils.process_group_utils import GroupInfo
from miles.backends.training_utils.loss import loss_function
from repoharness2.adapters.miles import faithful_dis_loss as fd
fd._cp_all_reduce_sum=lambda t,cp:t
T=lambda n=1,r=0:GroupInfo(rank=r,size=n,group=None)
def state(cp,r,dp=1):
 set_parallel_state(ParallelState(intra_dp=T(dp),intra_dp_cp=T(dp*cp),cp=T(cp,r),tp=T(),pp=T(),ep=T(),etp=T(),indep_dp=T(),is_pp_last_stage=True))
a=Namespace(qkv_format='thd',rollout_temperature=0.7,true_on_policy_mode=True,log_probs_chunk_size=-1,allgather_cp=False,rollout_top_p=.9,rollout_top_k=9,vocab_size=9,bf16=False,fp16=False,calculate_per_token_loss=False,loss_type='custom_loss',custom_loss_function_path='repoharness2.adapters.miles.faithful_dis_loss.faithful_dis_loss_function',recompute_loss_function=False,use_dynamic_global_batch_size=False,global_batch_size=2)
