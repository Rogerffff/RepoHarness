# 第三批原环境复现入口（内部材料）

本次只为冻结的11题整理原运行条件与本地证据，未派发审查或执行作业。详细参数、精确instance_id选择器、输入/输出hash及逐题测试命令见 [environment_replay_inventory.json](environment_replay_inventory.json)。此文件和清单含私有评分入口，不交公开读者。

| 题目 | 原运行入口及差异 |
| --- | --- |
| DVC 6954、3665、4785 | `dvc_install_v1c`派生镜像，加该批`replay_with_install_recipe.py --recipe recipes/<id>.json`；精确替换原安装段为`revised_install`，三题均使用`.[all,tests]`。没有`--materials`或`--bindings`。 |
| mypy 15139、15184、10174；Moto 6185、6408、5960 | `install_wave1`派生镜像只增加离线wheel及PIP环境变量，直接调用原`replay_grade.py run`；安装/测试spec保持原输入。三类wheel pins逐题记录，不能套用DVC安装覆写。 |
| Pandas 50319 | `reference_v1`使用原镜像；必需该批wrapper的`--bindings reference_bindings_v1.json`及同目录`reference_bindings.py`。原grader版本有`+reference-bindings-v1`，没有派生镜像或安装/测试材料覆写。 |
| Pandas 51605 | 原`baseline01`由`campaign.py -> worker.py -> ReplayGrader.replay_one`调用默认driver；精确jobs为`w06-1.json`第11/12项，未加recipe/materials/bindings。原jobs还含其它题，后续不能直接整份重跑。 |

DVC原输入是批次`recipes/<id>.json`，每个run的`recipe/recipe.json`及before/after脚本是审计输出。Pandas50319的原bindings输入有顶层`tasks`映射；run内同名`bindings/reference_bindings.json`只是本题条目，不可直接传给`--bindings`。本次已核对6份DVC recipe审计和2份Pandas bindings审计与各自原输入一致；全批未使用`--materials`。

各题原始`grading`与prepared私有行一致，spec vendor均为`swegym_constants_242429c1`；逐题版本、完整测试命令、scripts_digest和原镜像ID分别入表。9题使用本地派生镜像，2题Pandas使用原tag与预期manifest digest；两种ID不能混用。源码已有本地`frozen_sources/baseline.tar.gz`和`dvc.tar.gz`：CLI文件hash相同，内部replay/prepared_task_face版本不同，复现应按清单选择原快照。

共同原条件为2 CPU、4 GiB内存、PID512、deny_all网络，grader为`rh2grader/54322`，candidate应用身份为`agent/54321`；预算为candidate900秒、grading3600秒、cleanup120秒、pull1800秒。它们来自本题原账本，不代表actor环境已验收。

仍待准备：目标运行机镜像可用性未查；本地summary副本仍引用原`/work/full216_20260919`，该绝对路径在本机不存在，必须另备重定位summary/manifest和代码运行环境。原派生镜像的context/wheel payload未在本地副本保存，若镜像缺失需按逐题plan/pins与image审计重新准备。所有新输出路径和run_id另定，不覆写历史证据。本清单不是执行授权。
