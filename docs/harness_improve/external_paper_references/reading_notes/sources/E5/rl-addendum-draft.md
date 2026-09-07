# 交审后补充来源：SkyRL 的 SWE-smith 接线

日期2026-09-07；原稳定初稿尚未修改。本段拟替换最终笔记§7.2的有限追踪段，须由同一审查者定点核对。

沿官方RL链接继续追踪，找到SkyRL历史`swe-smith`分支的[提交58cfc213c0f7b44a0b5033e68d65782d05f8a13d](https://github.com/NovaSky-AI/SkyRL/commit/58cfc213c0f7b44a0b5033e68d65782d05f8a13d)，提交日期2025-06-05，消息为`support swesmith`。该版本`verl/workers/agentic/swe_agent/utils.py::get_instance_docker_image`识别`data_source`中的`swe-smith`、按任务`image_name`构造镜像名；`verl/workers/agentic/swe_agent/swesmith_utils.py::make_test_spec`调用当时SWE-smith的`get_test_command`生成测试脚本；`verl/workers/agentic/swe_agent/codeact.py::_evaluate_agent`/`_apply_patch_and_evaluate`根据dataset切到SWE-smith测试规范和`get_eval_report`。这提供具体的环境/评分接入证据。

同分支`examples/sky/swebench/run_skyrl_agent_oh7b_s1.sh`设置`algorithm.adv_estimator=grpo`、OpenHands-7B初始化、16条轨迹/题、最多15次agent迭代、lr1e-6、KL loss系数0.001、clip0.2；但脚本仍是SWE-Gym数据路径占位，`examples/sky/swebench/README.md`对应80/220/293数据，而非已钉死的SWE-smith训练集。因此这些字段只能说明该分支的通用RL示例，不能当成SWE-smith已跑实验配方。根README的SkyRL-Agent成绩没有在已读材料中证明由SWE-smith产生，不在本笔记归功于SWE-smith。

当前SkyRL main `0b286bacba2bb51dfe50186b6b5d6b1e0b5f5518` 已重组目录，所读`skyrl-agent/data/swe_data.py`与`skyrl-agent/examples/run_skyrl/run_skyrl_swe.sh`默认R2E-Gym。历史代码依赖旧`swesmith.harness.utils.get_test_command`等API，与本次SWE-smith C版本也不同；未作依赖复原或执行验证。结论是“官方宣布可用于GRPO，存在具体接线；没有从已核来源建立SWE-smith专属受控RL收益”，不是“只有一个无法追踪的链接”，也不是“论文40.2%来自RL”。
