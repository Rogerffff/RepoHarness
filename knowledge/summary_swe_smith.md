# 《SWE-smith: Scaling Data for Software Engineering Agents》阅读摘要

## 论文信息

- arXiv:2504.21798,v1 2025-04-30,v2 2025-05-21
- 作者:John Yang、Kilian Lieret、Carlos E. Jimenez、Alexander Wettig、Binyuan Hui 等(Stanford、Princeton、Alibaba Qwen 等)
- 发表:NeurIPS 2025 Datasets & Benchmarks track Spotlight(arXiv 页面未标注,由官方 GitHub 仓库标题与 NeurIPS 会议页确认)
- 官方页面:<https://arxiv.org/abs/2504.21798>;资产:<https://swesmith.com>

## 核心问题

现有 SWE agent 训练数据小而贵:至多千级实例、来自不超过 11 个 GitHub 仓库,收集需数百小时人力;且按任务实例各建执行环境导致数 TB 存储(SWE-gym Real 约 6TB、R2E-gym 子集约 4TB)。瓶颈在"从真实 PR 逆向构建任务"这条路线本身,论文改走"对任意 Python 仓自动注入 breaking 变更"的合成路线。

## 方法:注入式任务合成

1. 仓库选择:PyPI 下载量前 5,000 的包,过滤 <1,000 star,剔除 12 个 SWE-bench 测试仓,得 128 仓;每仓构建一个共享 Docker 镜像,同仓所有任务共用环境。
2. 五种 bug 生成策略(yield 率 / 每实例成本):LM Modify 在既有函数中注入 bug(56.0% / 0.38 美分);LM Rewrite 按函数签名+docstring 重写实现(35.0% / 3.93 美分);Procedural Modification 用 AST 随机变换如删条件/循环(40.2% / 0 美分);PR Mirror 用 LM 逆转真实 PR(33.8% / 5.53 美分);Bug Combination 合并多个 patch(96.9% / 0 美分)。
3. 判定与包装:能破坏仓库既有测试的变更即构成任务实例(原测试即 verifier),再用 LM 生成 issue 文本(均价 2.54 美分/条)。

## 规模与训练结果(带具体数字)

- 50,137 个任务实例 / 128 仓 / 执行环境总存储 295GB(仓库级共享镜像;任务线索中"125 个镜像"未能核实,论文口径是 128 仓各一个镜像)。
- 论文估算:同规模 50k 实例若按 SWE-bench 逐任务建环境需 50~150TB,约 500 倍差距。
- 生产成本:总计约 $1,360(bug 生成约 $1,000 + 仓库安装 $160 + issue 文本 $200),人工约 20 小时。
- 训练:以 Claude 3.7 Sonnet 为 expert 在 8,686 个任务实例上采轨迹(36% 被解出),去重后取 5,016 条(每任务至多 3 条)做 rejection-sampling SFT;未做 RL。
- SWE-agent-LM-32B(基座 Qwen2.5-Coder-32B-Instruct):SWE-bench Verified 40.2% pass@1(较基座 +33.4 点),SWE-bench Lite 30.7%;摘要称当时开源模型 SOTA。
- 附带产物:SWE-bench Multilingual,300 个实例、覆盖 9 种编程语言,用于评跨语言泛化。

## 重要限制

- 管线 Python-centric:程序化变换重度依赖 Python 的 ast 库,扩到其他语言需重做该层。
- 只演示了 SFT(rejection sampling fine-tuning),注入式任务在 RL 训练下的表现论文没有证据。
- expert 采样只覆盖被解出的 36% 实例,更难实例未进训练集(数据为论文所载,偏置影响属本摘要推断)。

## 对 RepoHarness 的意义

- 注入式合成是我们 E-Wave4 中成本最低的扩容路线:约 $1,360 + 20 人时产出 50k 实例,比生成式(从头造仓库与任务)低一个量级以上,且天然自带可执行 verifier(仓库既有测试)。
- 仓库级共享镜像(295GB vs 数 TB)直接回答我们的镜像存储设计:同仓任务共享环境是被验证可行的默认方案。
- 40.2% Verified 证明合成任务 SFT 可达实用水平;但注入任务的 verifier 是已知测试集,RL 下针对既有测试的 reward hacking 面需要我们自己验证,不能从本文外推。
- SWE-bench Multilingual 提示扩语言天花板:注入路线跨语言的第一道工程是替换 AST 变换层。
