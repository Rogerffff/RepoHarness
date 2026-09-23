# Infra07 最小检查：离线合同 + CPU 反例 + 固定 token 打分

这些文件是[训练—推理一致性专题](../../Infra07_train_inference_consistency.md)的研究附件，**不接生产训练、不修改 loss、不自动装模型、不清缓存、不发布权重**。2026-09-08 实际执行33个测试全部通过；其中HTTP只连接本地mock。真实SGLang/vLLM、HF、Megatron、CUDA与分布式路径尚未执行。

## 1. 立即运行已验证部分

在这个目录中运行：

```bash
python test_replay_check.py --output cpu_results_local.json
python -m py_compile replay_check.py test_replay_check.py
```

合同和HTTP测试仅用Python标准库；5个autograd/数值测试需要PyTorch，缺少时明确skip。原始[结果文件](cpu_results_20260908.json)记录本次实际环境 `Python 3.13.5 / torch 2.10.0+cpu`、33项名称、0失败、0跳过。以后重新运行请输出新文件，不覆盖历史记录。

这些测试检查**我们写的比较器和独立反例**，不是上游pytest。mock不模拟真实GPU调度、attention、MoE或缓存。

## 2. 一个可直接运行的离线正负对照

```bash
python - <<'PY'
import copy
from test_replay_check import fixture
from replay_check import write_json
reference = fixture()
changed = copy.deepcopy(reference)
changed['records'][0]['logprobs'][0] += 0.1
write_json('reference.synthetic.json', reference)
write_json('changed.synthetic.json', changed)
PY
python replay_check.py compare reference.synthetic.json reference.synthetic.json \
  --atol 0 --output same.synthetic.report.json
# 输出PASS，退出0。
python replay_check.py compare reference.synthetic.json changed.synthetic.json \
  --atol 0.000001 --output changed.synthetic.report.json
# 输出FAIL，退出1；这是预期负对照，不是命令无法运行。
```

状态：`PASS=0`、`FAIL=1`、`INCOMPARABLE=2`、`INSUFFICIENT=3`。前者只表示提供的固定样本在**声明合同**和指定绝对logprob容差下符合要求；不认证模型或checkpoint，也不输出一个假定已经测得的KL。

## 3. 比较文件格式

以下为**纯合成说明，不是目标模型的真实token**：

```json
{
  "schema": "infra07.fixed-token-logprobs.v1",
  "contract": {
    "weights": "exact-checkpoint-or-operator-label",
    "tokenizer": "tokenizer-and-template-revision",
    "context": "causal-text-no-padding-position0-v1",
    "probability": {"kind": "full_vocab", "temperature": 1.0, "processors": []}
  },
  "execution": {"backend": "synthetic-not-model", "cache": "not-applicable"},
  "records": [{
    "id": "call-a::r0",
    "input_ids": [1, 2, 3, 4],
    "positions": [1, 2, 3],
    "mask": [1, 0, 1],
    "logprobs": [-1.0, null, -2.0],
    "weight_labels": ["v1", "v1", "v1"]
  }]
}
```

`positions` 是目标token在完整 `input_ids` 中的位置；对应常规causal模型的logits行是 `position-1`。位置0不参与。`mask=0` 是观察／工具或明确排除的位置；占位null不进入数值统计，合法logprob为0的模型token则不能因为值为0而删除。

按 `id` 严格配对，重复和缺失均拒绝，不能静默取交集。token、位置、mask、权重标签及提供的attention/position/segment/routing字段不一致时返回INCOMPARABLE，而不是产生一个很大的“数值误差”。

支持集比较另设 `probability.kind="fixed_retained_support"`，每条record必须提供与positions对应的 `support_ids`；目标token必须在每个支持集中，两侧K必须一致。此时logprobs必须已经由实际后端在同一K上归一化；**比较器不具备完整logits，不能替你恢复支持集分布**。返回top-N logprobs不能替代这个K。

`weights` 和 `weight_labels` 是声明；脚本不知道GPU内参数是否真的对应它们。`routing_ids` 若缺失则不验证routing，不能把一次PASS写成R3验证通过。不同backend、dtype、batch可以记在execution中作为实验变量，但改变后是否仍应数值相近，必须由实验定义解释。

## 4. 真实 SGLang prefill：代码已提供，但本次未在真实服务运行

先从实际capture导出下面形状的 `frozen_cases.json`，**不要将合成示例ID直接用于模型**：

```text
{"cases": [{"id": "真实call身份", "input_ids": [...实际完整前缀和目标token...],
             "positions": [...所选目标位置...], "mask": [...对应0/1...]}]}
```

默认仅接受loopback服务；远程服务必须是你有权调用的隔离调试服务，并显式加 `--allow-remote`。API凭据可通过环境变量 `INFRA07_API_KEY` 传入，不写进输出。服务须已装载固定checkpoint、没有任何在途训练更新；保存服务启动配置、model dtype、量化、cache和backend信息。

```bash
python replay_check.py capture-sglang \
  --endpoint http://127.0.0.1:30000 \
  --cases frozen_cases.json --weights frozen-checkpoint-label \
  --tokenizer frozen-tokenizer-template-label \
  --concurrency 1 --repeats 1 --output sglang.prefill.c1.json

python replay_check.py capture-sglang \
  --endpoint http://127.0.0.1:30000 \
  --cases frozen_cases.json --weights frozen-checkpoint-label \
  --tokenizer frozen-tokenizer-template-label \
  --concurrency 4 --repeats 1 --output sglang.prefill.c4.json

# 下面阈值只是命令示例，不是GPU资格阈值；应在看结果前按实验设计选定。
python replay_check.py compare sglang.prefill.c1.json sglang.prefill.c4.json \
  --atol 0.00001 --output sglang.prefill.layout.report.json
```

请求固定为 `input_ids`、`return_logprob=true`、`logprob_start_len=0`、`max_new_tokens=0`、T=1、top-p=1、top-k=-1、min-p=0。严格检查返回数组从位置0开始且token身份一致；版本API格式不同就明确失败，不猜测裁剪或shift。

限制：这测prefill scoring，不是原始decode replay；客户端并发不等于GPU batch；cache命中与input logprob支持依版本而异；max_new_tokens=0也会占用服务资源。脚本不自动flush任何服务、不改并发配置、不安装依赖。真实服务响应尚未验证，因此mock通过只是协议测试。

## 5. 本地 HF eager 参照：只提供未运行的可选入口

需要已安装兼容的PyTorch/Transformers，以及已经下载到本机的可信模型。使用 `local_files_only=True` 与 `trust_remote_code=False`，不会为了适配模型执行其自定义远程代码。先选几条短序列，标准HF forward会生成完整位置的logits，长序列大词表可能耗尽显存。

```bash
python replay_check.py score-hf --model-dir /absolute/path/to/model \
  --device cuda:0 --dtype bfloat16 \
  --cases frozen_cases.json --weights frozen-checkpoint-label \
  --tokenizer frozen-tokenizer-template-label --output hf.eager.json

python replay_check.py compare sglang.prefill.c1.json hf.eager.json \
  --atol 0.00001 --output cross_backend.report.json
```

HF入口只做纯文本、无padding、普通causal attention，强制eval、不建KV cache，logits转换fp32后log-softmax。**它不是Megatron actor、不执行TP/CP，也不回放MoE专家**；实际项目trainer必须另导出同一schema，而且比较前要核实权重转换一致。这里的数值容差仍只是示例。

## 6. 真正 decode／正式 faithful DIS 怎样补

保留真实生成的 `output_token_logprobs` 与 `output_token_sampling_logprobs` 两列，别用prefill重算覆盖。第一条用于合适条件下的原始分布诊断，第二条加实际支持集用于正式目标的对照。项目 `faithful_dis_loss.py` 已强制支持集重放；**本全词表debug脚本不建议修改该训练合同**。

现有miles dump只有局部index和CP切片等信息，需借用已有rh2身份和全局位置构造导出；不能按rank文件顺序拼接。在没有真实token、K、权重或CP映射时，保留缺口，不伪造一组“看起来接近”的数据。
