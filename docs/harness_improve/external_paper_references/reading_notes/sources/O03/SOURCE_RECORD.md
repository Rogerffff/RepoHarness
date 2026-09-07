# O03 来源与附件记录

读取日期：2026-09-07。附件只用于论文精读、版本比较和静态复现核对；未运行训练、测试镜像或 benchmark，未下载权重或 parquet 数据。

## 论文与版本

- [arXiv v1 PDF](2504.07164v1.pdf)：https://arxiv.org/pdf/2504.07164v1 ，27 页，2025-04-09 v1。
- [TeX 原始压缩包](2504.07164v1.tar.gz)：https://arxiv.org/src/2504.07164v1 。解压入口 [main-arxiv.tex](tex/main-arxiv.tex)，实际正文为 sec/0_abstract_v3、1_intro、2_system、3_agents、4_inference、5_related、6_conclusion；附录为 appendix/dataset、training、inference、examples（包含 E 轨迹图）。包内注释和未使用图片不当作论文新增实验。
- [arXiv 文本](paper.txt) / [官网 PDF](project-paper.pdf) / [官网 PDF 文本](project-paper.txt)。官网 PDF URL：https://r2e-gym.github.io/assets/paper.pdf 。全部正文/附录提取文本去除水印、统一空白后相同；另将 p.2–27 以 Poppler 60 DPI 渲染，对应 PNG 字节均相同；p.1 的 arXiv 水印/版面差异不作逐像素等同。
- [arXiv 摘要页](arxiv_abs.html) / [项目网页](project_page.html)：分别从 https://arxiv.org/abs/2504.07164 和 https://r2e-gym.github.io/ 保存。摘要页面名和任务数与 PDF 有差异，详见正文。
- rendered/ 保存 PDF p.2/3/5/6/7/8/9/15/22/23/26/27 的原页渲染，供图表公式与图像轨迹核查。

## 代码

官方仓库 https://github.com/R2E-Gym/R2E-Gym ，读取 commit `0d94c4eb9431cd195c55a7ea3abd54006c9a1735`。`official_repo/` 是此 commit 的必要文件摘录，保持完整仓库相对路径，含 LICENSE；它不是完整可安装 checkout。当前版本含后来的 DeepSWE 相关变化，不作为 v1 论文实验版本 pin。

已保留文件：

- [README.md](official_repo/README.md)
- [LICENSE](official_repo/LICENSE)
- [docs/ENV_GENERATION.md](official_repo/docs/ENV_GENERATION.md)
- [train/dataset_info.json](official_repo/train/dataset_info.json)
- [train/train_r2egym_14B_verifier.yaml](official_repo/train/train_r2egym_14B_verifier.yaml)
- [train/train_r2egym_32B_agent.yaml](official_repo/train/train_r2egym_32B_agent.yaml)
- [train/train_r2egym_32B_testing_agent.yaml](official_repo/train/train_r2egym_32B_testing_agent.yaml)
- [src/r2egym/repo_analysis/constants.py](official_repo/src/r2egym/repo_analysis/constants.py)
- [src/r2egym/repo_analysis/repo_analysis_args.py](official_repo/src/r2egym/repo_analysis/repo_analysis_args.py)
- [src/r2egym/repo_analysis/store_repo_commits.py](official_repo/src/r2egym/repo_analysis/store_repo_commits.py)
- [src/r2egym/repo_analysis/analyze_testable_commits.py](official_repo/src/r2egym/repo_analysis/analyze_testable_commits.py)
- [src/r2egym/repo_analysis/repo_testextract.py](official_repo/src/r2egym/repo_analysis/repo_testextract.py)
- [src/r2egym/repo_analysis/repo_testheuristics.py](official_repo/src/r2egym/repo_analysis/repo_testheuristics.py)
- [src/r2egym/agenthub/environment/env.py](official_repo/src/r2egym/agenthub/environment/env.py)
- [src/r2egym/agenthub/runtime/docker.py](official_repo/src/r2egym/agenthub/runtime/docker.py)
- [src/r2egym/agenthub/agent/agent.py](official_repo/src/r2egym/agenthub/agent/agent.py)
- [src/r2egym/agenthub/trajectory/trajectory.py](official_repo/src/r2egym/agenthub/trajectory/trajectory.py)
- [src/r2egym/agenthub/run/edit.py](official_repo/src/r2egym/agenthub/run/edit.py)
- [src/r2egym/agenthub/config/r2egym/edit_fn_calling.yaml](official_repo/src/r2egym/agenthub/config/r2egym/edit_fn_calling.yaml)
- [src/r2egym/agenthub/config/r2egym/edit_non_fn_calling.yaml](official_repo/src/r2egym/agenthub/config/r2egym/edit_non_fn_calling.yaml)
- [src/r2egym/agenthub/verifiers/create_bestofn_aggregate.py](official_repo/src/r2egym/agenthub/verifiers/create_bestofn_aggregate.py)
- [src/r2egym/agenthub/verifiers/run_eb_verifier.py](official_repo/src/r2egym/agenthub/verifiers/run_eb_verifier.py)
- [src/r2egym/agenthub/verifiers/run_ef_verifier.py](official_repo/src/r2egym/agenthub/verifiers/run_ef_verifier.py)
- [src/r2egym/agenthub/verifiers/prepare_ef_verifier_input.py](official_repo/src/r2egym/agenthub/verifiers/prepare_ef_verifier_input.py)
- [src/r2egym/agenthub/verifiers/run_regression_tests.py](official_repo/src/r2egym/agenthub/verifiers/run_regression_tests.py)
- [src/r2egym/agenthub/verifiers/run_reproduction_tests.py](official_repo/src/r2egym/agenthub/verifiers/run_reproduction_tests.py)

## Hugging Face 元数据

通过 `https://huggingface.co/api/datasets/R2E-Gym/<name>` 或 `https://huggingface.co/api/models/R2E-Gym/<name>` 获取；组织列表另存 `hf_org_models.json`、`hf_org_datasets.json`，初次探测结果含 401 入口存 `hf_asset_summary.json`。401 不区分私有、不可用或改名，不解释为明确删除。行数来自卡片 schema，未逐行检查。

| 快照 | 资产 ID | revision | 卡片 split 行数 |
| --- | --- | --- | --- |
| [hf_R2E-Gym-Lite.json](hf_R2E-Gym-Lite.json) | `R2E-Gym/R2E-Gym-Lite` | `8d3163011f01f9393bb3dc7700497a79a8686ae5` | train=4578; dev_10pr_v1=100; dev_100pr_v1=1000; dev_200pr_v1=1876; dev_100pr_v2=1000; dev_100pr_v3=876; dev_100pr_v4=575; dev_100pr_v5=782; dev_100pr_v6=701; dev_100pr_v7=300 |
| [hf_R2E-Gym-Subset.json](hf_R2E-Gym-Subset.json) | `R2E-Gym/R2E-Gym-Subset` | `2e8108ff942f24fcb5686badfaf7f9a8808566d5` | train=4578 |
| [hf_R2E-Gym-V1.json](hf_R2E-Gym-V1.json) | `R2E-Gym/R2E-Gym-V1` | `903d405799ac435061c41e72260c81ca5100f964` | train=8101 |
| [hf_R2E-TestgenAgent-Patches.json](hf_R2E-TestgenAgent-Patches.json) | `R2E-Gym/R2E-TestgenAgent-Patches` | `005f0eb8c80cb93f3cbfe8699590f752a1c514c3` | train=200 |
| [hf_R2E-TestgenAgent.json](hf_R2E-TestgenAgent.json) | `R2E-Gym/R2E-TestgenAgent` | `e91db21ab3069ac8f3fdcdc98c13046c5527be84` |  |
| [hf_R2EGym-32B-Agent.json](hf_R2EGym-32B-Agent.json) | `R2E-Gym/R2EGym-32B-Agent` | `b7b39e295ca764d57ae05b72122da9659e1731b3` |  |
| [hf_R2EGym-SFT-Trajectories.json](hf_R2EGym-SFT-Trajectories.json) | `R2E-Gym/R2EGym-SFT-Trajectories` | `63ab4eb37668f8be0104133c21d896bedbcf8404` | train=3231 |
| [hf_R2EGym-TestingAgent-SFT-Trajectories.json](hf_R2EGym-TestingAgent-SFT-Trajectories.json) | `R2E-Gym/R2EGym-TestingAgent-SFT-Trajectories` | `0cfc507e195ff875fa622ab5cd4403d4a7409c46` | train=2281 |
| [hf_R2EGym-Verifier-Trajectories.json](hf_R2EGym-Verifier-Trajectories.json) | `R2E-Gym/R2EGym-Verifier-Trajectories` | `d8340c4605bb1a00a206a1978813cee35daeff8c` | train=5750 |
| [hf_R2EGym-Verifier.json](hf_R2EGym-Verifier.json) | `R2E-Gym/R2EGym-Verifier` | `623145b2adfdfa3ed59063899480a568811bf5e3` |  |

名称差异已核：测试 agent 实际公开入口为 R2E-TestgenAgent，verifier 为 R2EGym-Verifier。README 所列 R2E-Gym-Full 探测 401，但组织有 R2E-Gym-V1；其 8,101 行不与论文 8,135 强行统一。多数模型和轨迹 cardData 未填 license，不据此推断允许或禁止使用。

## 审查版本

稳定初稿副本 [O03_r2e_gym.draft_20260907.txt](O03_r2e_gym.draft_20260907.txt) 只用于固定审查输入；内部链接按正式笔记所在目录解析，不作为第二份正式笔记。完整独立审查记录由 ../../reviews/12_O03_review.md 提供。
