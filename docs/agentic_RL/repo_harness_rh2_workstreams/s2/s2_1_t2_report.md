# S2-1 T2 报告：契约与 runner（进行中，按进展追加）

日期：2026-07-13 起。依据：执行计划 §4 T2。前置：T1 已关闭（2026-07-13，用户确认）。

## T2-a 风险 F 探测与关闭（2026-07-13）

执行计划风险 F（"SWE-Gym 的 eval_script 生成——swebench 库的 version→spec 映射是否覆盖这些仓库未验证"）**实锤且已关闭**：

```text
探测 1：swebench 4.1.0 官方 MAP_REPO_VERSION_TO_SPECS
  → SWE-Gym Lite 全部 11 个仓库 0 覆盖（MONAI/moto/mypy/dvc/dask/conan/
    modin/pandas/pydantic/bokeh/hydra 都不是 SWE-bench 官方 12 仓库）
  → 官方 make_test_spec 对 216 题一题都生成不了。
探测 2：SWE-Gym/SWE-Bench-Fork@main（commit 242429c188fc…）constants.py
  → 216/216 survivor 的 (repo, version) 全覆盖（33 仓库 / 808 spec 对，
    含 install / test_cmd / python 版本，dvc 另有 pre_install）。
排障插曲（有教学价值）：首次覆盖检查漏报 26 条 MONAI——fork 文件末行把
  MAP_REPO_VERSION_TO_SPECS 重绑定为小写键版本，查表必须 repo.lower()。
  这与 T1 的镜像名小写化是同一个坑的两次出现：**repo 身份的大小写归一化
  必须在 T2 的规范化 repo identity 里显式定案**（内部权威 = 原始大小写
  owner/name；对 docker registry 与 spec 表查询用小写投影）。
```

**处置**：fork constants 以 commit pin `242429c1` vendor 为冻结资产
`vendor/swegym_constants_242429c1.py`（逐字节原样 + 旁置 provenance JSON：
来源 URL/commit/取回时间/sha256/许可注记/覆盖验证结论），登记入
`s2_1_manifest_v0.json`。T2 的门 runner 与 eval 命令生成只消费该 vendor
文件（importlib 按路径加载），不在运行期访问 GitHub。

**对门 runner 形态的推论**（T2-b 设计输入）：SWE-Gym 的 xingyaoww 镜像是
预构建的（conda 环境与依赖已装好，install 命令在镜像构建期已执行），
运行期评分 = 容器内 `test_cmd + 测试选择器` + 官方 log parser——比官方
eval_script（含 checkout/install 全流程）轻；与 S1-4 clean grading 的
"干净容器 apply patch → 跑测试 → parser"结构一致，`grade_controlled_patch`
入口按此对接。install/pre_install 字段保留在 vendor 资产里备用（若实测
发现镜像内环境不完整再启用，先不进主路径）。

## 待续

T2-b：bundle v2 三分契约 + EXTRA_SCHEMA_REGISTRY 注册 + 契约测试。
T2-c：ingestion 构造器（strip_spec 驱动 + D5 收编 + task_id/duplicate
cluster 去重语义 + 大小写归一化的 repo identity）。
T2-d：`grade_controlled_patch` 受控入口。
T2-e：门 runner + fixture（§3.1 规格）+ `EnvValidationReport`。
