"""S1-7a debug training transport step 的接线胶水（远程 GPU 实机专用）。

本包不是 rh2 库面的一部分：它把 `repoharness2.adapters.slime.generate` 的
编排本体接到**真实** slime 训练栈（slime pin 镜像内的 AnthropicAdapter /
TrajectoryManager / ClaudeCodeHarness / SGLang patch 引擎）上，产出 A1/A2/A3
验收证据。文件分工：

- docker_sandbox.py  slime Sandbox 协议的 docker 容器实现（rollout 容器复用）
- capture_wire.py    call_sglang_generate 替换（tape flag 注入 + A4 捕获回填）
- glue.py            服务单例 + startup_checks 真实执行 + custom_generate 入口
- make_prompt_data.py  8 题冻结集 -> slime JSONL
- verify_transport.py  训练侧 rollout dump 与治理侧投影的逐位核对（A2 证据）
"""
