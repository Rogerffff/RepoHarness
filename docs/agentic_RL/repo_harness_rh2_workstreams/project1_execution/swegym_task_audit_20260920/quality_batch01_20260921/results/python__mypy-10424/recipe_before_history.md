# python__mypy-10424：历史前配方原件补记

2026-09-21，仍未放行/读取质量 history。`analysis_before_history.md` 已落盘后协调者提供本题原始配方位置；保留前稿不改，本补记只补齐其中“配方原件待提供”的缺项。

读取 `R/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-10424/image.json:1–12`、同目录 `build.log:1–32`，以及协调者限定的 `install_wave1/run_install_wave1.py:23–58`，R 为 `${REPO_ROOT}`。

- image.json 的 base digest 与本题 public bundle 相同，derived image ID 与两份原始账本相同（`sha256:362a2da70c5f90f6b7909ed92a8a8bceb9d9377cf822c0b170f45bc48f3e2a08`）。完整 Dockerfile 只 COPY wheels 到 `/opt/rh2/build-wheels` 并设置 `PIP_NO_INDEX=1`、`PIP_FIND_LINKS`，不修改业务源码、测试选择器或 expected。
- 本题固定 wheel 为 setuptools 75.1.0、wheel 0.44.0、packaging 24.1。共享构建脚本 32–47 要求每 pin 恰有一 wheel，构建后断言旧层保留；本题 build.log 22–28 记录实际 COPY 和该 image ID 输出。构建的 ARG 缺默认值 warning 不等于构建失败。
- 脚本 54–58 直接调用原 replay_grade.py 并传 `--derived-image`、recipe 名；未使用其它波次的 revised_install wrapper。原始评估日志仍执行既有 requirements + editable 安装。
- 因而本次历史 grader 对照的环境修复范围可解释为离线构建 wheel 预置。前稿看到的 test-requirements.txt 增加 types-typing-extensions 已存在于来源镜像/初态，不能归因给这个只 COPY 的派生层。
- 未读取全部 wheel 内容或证明其内容无答案；未检查真实 actor 是否使用这份派生镜像，也未执行重建。这项补记不解除 actor 侧待验与窄覆盖风险。

本补记属于前历史证据集合；不更改 analysis_before_history 的初判或下一实验。
