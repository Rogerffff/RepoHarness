"""用当前缓存 tokenizer 辅助解释历史 token，不能代替原始 ID 对比。"""
import json,struct
from pathlib import Path
from transformers import AutoTokenizer
tok=AutoTokenizer.from_pretrained('Qwen/Qwen3-30B-A3B',revision='ad44e777bcd18fa416d9da3bd8f70d33ebb85d39',local_files_only=True)
D=next(p for p in Path(__file__).resolve().parents if (p/'rh2/pyproject.toml').is_file())/'docs/agentic_RL/repo_harness_rh2_workstreams/s1/7a_artifacts/artifacts_run8/rollouts/4a25c5a4-f07f-422b-a6a4-'
c=json.loads((D/'capture_records.json').read_text())
def read(r):
 b=(D/'tapes'/f"{r['ref_id']}.bin").read_bytes();return list(struct.unpack('<'+'i'*(len(b)//4),b))
a=read(c[0]['response_token_ids_ref']);p=read(c[0]['prompt_token_ids_ref']);b=read(c[1]['prompt_token_ids_ref']);n=19064-len(p)
# 仅看响应尾部结构，不输出题目上下文。
print(json.dumps(dict(decoder_model='当前缓存30B分词器，仅辅助解码历史4B IDs，token级比对不依赖此解码',response_prefix=tok.decode(a[:4]),old_tail=tok.decode(a[max(0,n-30):]),new_tail=tok.decode(b[len(p)+n-30:len(p)+n+90]),special_think_id=tok.convert_tokens_to_ids('<think>')),ensure_ascii=False,indent=2))
