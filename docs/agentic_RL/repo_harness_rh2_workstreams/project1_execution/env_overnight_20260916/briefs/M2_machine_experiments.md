# M2 · 机器 2：依赖/资产/网络调查（③）与反例执行（④）、镜像静态泄漏扫描

机器 2 只归本包使用（协调者派发消息给出 SSH 命令；不写进文件）。布局：`/work/code/rh2`（rsync 自本机，含 `.venv` 由 `uv sync --locked --group swe --group dev` 建好）、`/work/code/docs/.../s2`、`/work/envscreen/M2/`（你的输出）。镜像清单在 `/work/envscreen/M2/images.txt`，协调者已在后台拉取（`/work/envscreen/M2/pull.log` 出现 `PULLS_DONE` 即完成；未完成时只用已存在的镜像）。

## 机器纪律
- 每个实验一个容器名前缀 `envscreen-m2-<题>-<序号>`，用完 `docker rm -f`；不做全局 prune；并发容器 ≤ 3；每容器 `--memory 8g --cpus 4`（实验容器不是正式 grader，可比正式 profile 宽，但要记录）。
- **绝不 `docker commit`**（本机 overlay2 + metacopy/native-diff 组合下 commit 会把 chown 过的文件内容写成全 0，见 `swe_grading_wiring_20260915/e1_codex_review_20260916.md` §2）。派生镜像只能 `docker build -f Dockerfile`，构建期间 `echo N > /sys/module/overlay/parameters/metacopy`，构建后按 `swe_grading_wiring_20260915/derived_images/build_derived.sh` 的方法核对基础镜像与派生镜像若干文件 sha256 相同，再 `echo Y` 回去（正式链的 chown 需要 metacopy=Y 才快）。
- 联网只用于：拉镜像、在"准备阶段"容器里下载 wheel/权重/数据；所有下载记录 URL、大小、sha256、放置路径、对候选用户（uid 54322，HOME=/home/rh2grader）是否可读。**检查预置的 wheel 缓存里没有目标包（moto/pydantic/pandas/…）本身或其修复版本。**
- 以实际非 root 身份验证：`useradd -u 54322 rh2grader`，`docker exec -u 54322 -e HOME=/home/rh2grader …`。

## 工作项（按顺序，每项落盘到 `/work/envscreen/M2/<项>/` 并同步到本机 `runs/env_overnight_20260916/M2/`，报告写本机包目录）
1. **安装/构建配方（③）**：对 mypy-12741、pydantic-8500、pandas-48106、moto-6913、dask-7894、conan-13326 各一次：在 fresh 容器里以候选用户执行来源 `install` 串（从 `rh2/src/repoharness2/envpack/spec_vendor.py` 的 `derive_install_cmd` 取），分别在 `--network none` 与联网两种条件下；记录每条子命令的退出码、失败原因、`pip freeze` 前后差异、导入路径与版本串、编译产物；判断离线需要预置什么（wheel 清单）。产出 `recipes/<repo>-<version>.json`（安装串、离线失败原因、所需预置、验证命令、实际用户/路径/耗时）。
2. **资产（③）**：MONAI-1121（torchvision ResNet 权重）、MONAI-3205（Hippocampus 数据）：找出测试实际请求的 URL 与缓存路径（用 `--network none` 跑相关测试看报错，再联网准备阶段下载），确定候选用户可读的放置路径与需要的环境变量（`TORCH_HOME` 等），验证 deny_all 下相关测试通过。产出 `assets/<题>.json`。
3. **服务/网络（③）**：moto-4799、moto-6913、modin-6937：定位依赖真实端点的测试（`--network none` 下失败或行为改变的测试 ID），给出本地桩方案（moto server / 环境变量）并验证；记录"有网/无网"逐测试状态差异。产出 `network/<题>.json`。
4. **反例执行（④）**：等本机 L3 包在 `docs/.../env_overnight_20260916/L3_trajectories/counterexamples/` 写出脚本后（协调者会 rsync 到 `/work/envscreen/M2/counterexamples/` 并发消息通知你），按每题 `run_matrix.sh` 在 base / gold / candidate 三种状态跑诊断测试与相关官方测试，保存 JSON 结果与日志到 `counterexamples/<题>/results/`。若脚本未到，先做 1–3。
5. **静态泄漏扫描**：对本机全部已拉取镜像各起一个 `--network none` 容器执行：`git -C /testbed log --all --oneline | head`、`git rev-list --all --count`、`git tag`、`git remote -v`、`git fsck --lost-found | grep -c dangling`、`git status --porcelain | wc -l`、检查 HEAD 之后是否有可达提交、conda 环境里目标包的版本与安装位置（`pip show <pkg>`）、`pip cache dir` 大小；产出 `leak_scan/<镜像>.json` 与汇总表。
6. 报告 `M2_report.md`：配方表、资产表、网络表、反例结果表、泄漏扫描汇总、需要用户决定的问题、机器与磁盘占用、残留容器检查（应为 0）。

到本机时间 08:30 停止新实验；写完当前项，`docker ps -a` 确认无本包容器残留。
