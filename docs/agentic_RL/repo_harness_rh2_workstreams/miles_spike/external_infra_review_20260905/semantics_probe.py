"""独立 logits/梯度 oracle；CPU 与模拟 CP 分片，不证明 GPU。"""
from probe_bootstrap import *
random.seed(31);torch.manual_seed(31)
max_err=max_gerr=0.; cases=0
for seed in range(12):
 totals=[random.randrange(3,17) for _ in range(3)]
 resps=[random.randrange(1,x) for x in totals]
 toks=[torch.randint(0,9,(l,)) for l in totals]
 logs=[torch.randn(l,9,dtype=torch.float64) for l in totals]
 masks=[torch.tensor([1]+[random.randrange(2) for _ in range(r-1)]) for r in resps]
 ids=[]; offs=[]; support=[]; behaviors=[]
 for i,(r,t) in enumerate(zip(resps,totals)):
  sups=[]; ix=[]; off=[0]; b=[]
  for j in range(r):
   target=int(toks[i][t-r+j]);sup=sorted({target,random.randrange(9),random.randrange(9)}) if masks[i][j] else [target]
   sups.append(sup);ix+=sup;off.append(len(ix))
   z=logs[i][t-r+j-1][sup]/.7
   lp=float(z[sup.index(target)]-torch.logsumexp(z,0))
   b.append(lp-random.choice([-.6,.3,-2.,1.8]))
  ids.append(ix);offs.append(off);support.append(sups);behaviors.append(torch.tensor(b,dtype=torch.float64))
 adv=[torch.full((r,),v,dtype=torch.float64) for r,v in zip(resps,[.7,.7,-.7])]
 den=[int(masks[0].sum()+masks[1].sum())]*2+[int(masks[2].sum())]
 oracle_logs=[x.clone().requires_grad_() for x in logs]; oracle=torch.tensor(0.,dtype=torch.float64)
 for i,(t,r) in enumerate(zip(totals,resps)):
  for j in range(r):
   target=int(toks[i][t-r+j]);sup=support[i][j];z=oracle_logs[i][t-r+j-1][sup]/.7
   lp=z[sup.index(target)]-torch.logsumexp(z,0);delta=float(lp.detach()-behaviors[i][j]);w=math.exp(delta) if math.log(.2)<delta<math.log(4) else 0.
   oracle=oracle-w*adv[i][j]*lp*masks[i][j]/den[i]/2
 oracle.backward()
 for cp in [1,2,3,4]:
  for fmt in ['thd','bshd']:
   a.qkv_format=fmt; maxseq=(max(totals)+2*cp-1)//(2*cp)*(2*cp)
   got=0.; grads=[torch.zeros_like(l) for l in logs]
   for rank in range(cp):
    state(cp,rank);local_tok=[];local_log=[];inds=[];local_b=[];local_a=[]
    for i,(t,r) in enumerate(zip(totals,resps)):
     if cp==1: rows=list(range(maxseq if fmt=='bshd' else t))
     else:
      ch=math.ceil((maxseq if fmt=='bshd' else t)/(2*cp));rows=list(range(rank*ch,(rank+1)*ch))+list(range((2*cp-1-rank)*ch,(2*cp-rank)*ch))
     local_tok.append(torch.tensor([int(toks[i][k]) if k<t else 0 for k in rows]));local_log.append(torch.stack([logs[i][k] if k<t else torch.zeros(9,dtype=torch.float64) for k in rows]));inds.append(rows)
     rs=[k-(t-r-1) for k in rows if t-r-1<=k<t-1];local_b.append(behaviors[i][rs]);local_a.append(adv[i][rs])
    lt=(torch.stack(local_tok) if fmt=='bshd' else torch.cat(local_tok)[None,:]); ll=(torch.stack(local_log) if fmt=='bshd' else torch.cat(local_log)[None,:,:]).requires_grad_()
    batch=dict(tokens=lt,unconcat_tokens=toks,total_lengths=totals,response_lengths=resps,loss_masks=masks,rollout_mask_sums=torch.tensor(den),advantages=local_a,rollout_log_probs=local_b,rollout_sampling_mask_ids=ids,rollout_sampling_mask_offsets=offs)
    if fmt=='bshd':batch['max_seq_lens']=[maxseq]*3
    loss,_,_=loss_function(a,batch,3,ll,True,2)
    scaled=loss/(3*cp);scaled.backward(); got+=float(scaled.detach())
    gg=ll.grad if fmt=='bshd' else ll.grad[0].split([len(x) for x in inds])
    for i,rows in enumerate(inds):
     for local,k in enumerate(rows):
      if k<totals[i]:grads[i][k]+=gg[i][local]
   err=abs(got-float(oracle.detach())); gerr=max(float((g-x.grad).abs().max()) for g,x in zip(grads,oracle_logs));max_err=max(err,max_err);max_gerr=max(gerr,max_gerr); cases+=1
   assert err<2e-7 and gerr<2e-7,(seed,cp,fmt,totals,resps,err,gerr)
print(dict(cases=cases,max_loss_error=max_err,max_logit_grad_error=max_gerr,scope='真实 loss dispatcher + faithful DIS + reducer; 独立 support log_softmax oracle; CPU true_on_policy; CP计数collective替换为恒等;不证明GPU'))
