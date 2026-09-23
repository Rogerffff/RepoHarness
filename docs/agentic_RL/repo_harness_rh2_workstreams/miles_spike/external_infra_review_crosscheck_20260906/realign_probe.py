import sys,json,copy
from pathlib import Path
R=next(p for p in Path(__file__).resolve().parents if (p/'rh2/pyproject.toml').is_file());sys.path.insert(0,str(R/'rh2/src'))
from transformers import AutoTokenizer
from slime.agent.adapters.anthropic import _translate_messages
from slime.agent.adapters.common import _render_token_ids
from slime.agent.trajectory import TrajectoryManager,TurnRecord,_SampleBuilder
from slime.utils.types import Sample
from repoharness2.adapters.slime.turn_identity import export_leaf_identity_spans
TOKENIZER_REVISION='ad44e777bcd18fa416d9da3bd8f70d33ebb85d39'
tok=AutoTokenizer.from_pretrained('Qwen/Qwen3-30B-A3B',revision=TOKENIZER_REVISION,local_files_only=True)
initial=[{'role':'user','content':[{'type':'text','text':'Solve task'}]}]
asst={'role':'assistant','content':[{'type':'thinking','thinking':'First reason'},{'type':'tool_use','id':'abc','name':'bash','input':{'command':'pwd'}}]}
user={'role':'user','content':[{'type':'tool_result','tool_use_id':'abc','content':'/repo'}]}
m0=_translate_messages(initial,None);p0=_render_token_ids(m0,tok,tools=None)
# 使用真实模板生成可以无漂移回放的工具响应；不假设decode文字相等就代表token相等。
canonical=tok.apply_chat_template(_translate_messages(initial+[asst],None),tools=None,tokenize=False,add_generation_prompt=False)
prefix=tok.decode(p0,skip_special_tokens=False)
assert canonical.startswith(prefix)
out0=tok.encode(canonical[len(prefix):],add_special_tokens=False)
assert p0+out0==tok.encode(canonical,add_special_tokens=False)
base_message=_translate_messages([asst],None)[0]
results=[]
for name,reminder,omit_thinking,long_first,long_second in [('clean_tool_only',False,False,False,False),('reminder',True,False,False,False),('reminder_long_next',True,False,False,True),('reminder_long_previous',True,False,True,False),('replay_omits_thinking',False,True,False,False)]:
 a=copy.deepcopy(asst);u=copy.deepcopy(user);out=list(out0)
 if long_first:
  a['content'][0]['thinking']=' '.join(['reason']*1100)
  c=tok.apply_chat_template(_translate_messages(initial+[a],None),tools=None,tokenize=False,add_generation_prompt=False)
  out=tok.encode(c[len(prefix):],add_special_tokens=False)
 original=_translate_messages([a],None)[0]
 if omit_thinking:a['content']=[b for b in a['content'] if b['type']!='thinking']
 if reminder:u['content'].append({'type':'text','text':'<system-reminder>continue</system-reminder>'})
 m1=_translate_messages(initial+[a,u],None);p1=_render_token_ids(m1,tok,tools=None)
 out1=([tok.encode('x',add_special_tokens=False)[0]]*1024 if long_second else tok.encode('next<|im_end|>',add_special_tokens=False))
 t0=TurnRecord(p0,out,'stop',[-.5]*len(out));t1=TurnRecord(p1,out1,'stop',[-.5]*len(out1))
 b=_SampleBuilder(1024);b.append_turn(t0,b.classify_token_drift(t0));drift=b.classify_token_drift(t1).value
 manager=TrajectoryManager();manager.record_turn('s',turn=t0,prompt_messages=m0,response_message=original);manager.record_turn('s',turn=t1,prompt_messages=m1,response_message={'role':'assistant','content':'next'})
 root=manager._trees['s']; exports=export_leaf_identity_spans(root,fork_threshold=1024)
 samples=manager.get_trajectory('s',base_sample=Sample(index=0,group_index=0))
 trained=sorted({turn for e in exports for _,_,turn in e.spans})
 generated=len(out)+len(out1);train_tokens=sum(sum(s.loss_mask) for s in samples)
 assert all(s.tokens==e.tokens and s.loss_mask==e.loss_mask for s,e in zip(samples,exports))
 results.append(dict(case=name,t0_tokens=len(out),t1_tokens=len(out1),builder_classification=drift,trained_turn_indices=trained,generated_tokens=generated,trained_tokens=train_tokens,leaf_count=len(samples)))
# 模板设置反例：当前实际HF模板不读clear_thinking；仅换kwargs无效。
u=copy.deepcopy(user);u['content'].append({'type':'text','text':'<system-reminder>continue</system-reminder>'})
messages=_translate_messages(initial+[asst,u],None)
x=tok.apply_chat_template(messages,tools=None,tokenize=True,add_generation_prompt=True)
y=tok.apply_chat_template(messages,tools=None,tokenize=True,add_generation_prompt=True,clear_thinking=False)
print(json.dumps(dict(tokenizer_snapshot=TOKENIZER_REVISION,template_mentions_clear_thinking='clear_thinking' in tok.chat_template,clear_thinking_false_changes_render=x!=y,cases=results),ensure_ascii=False,indent=2))
assert [(r['case'],r['trained_tokens']) for r in results] == [('clean_tool_only',29),('reminder',2),('reminder_long_next',1051),('reminder_long_previous',2),('replay_omits_thinking',2)]
assert x==y
