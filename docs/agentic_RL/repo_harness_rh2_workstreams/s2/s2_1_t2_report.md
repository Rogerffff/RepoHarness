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
`vendor/swegym_constants_242429c1.py`（逐字节原样 + 旁置 provenance JSON），
登记入 `s2_1_manifest_v0.json`。~~门 runner importlib 按路径加载~~
**（轮次 12 修正）消费模型**：构建期 `extract_vendor_specs.py` 一次性
exec vendored Python 提取为规范化 JSON（`vendor/swegym_specs_242429c1.json`）；
运行期只读 JSON 并核对 `envpack/spec_vendor.py` 固定注册表的 pinned sha256
——**永不在运行期 exec vendored 代码，也不接受 artifact 里的文件路径**。

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

## T2-b 修订（2026-07-13，codex 轮次 12 → 契约加固后 T2-c 才开工）

四条全部成立并修复：

```text
严重 1 身份交叉核对缺失：build_environment_package 只查 instance_id，
  public.repo/base_commit 与 grading 不一致也能组包（模型解 A 仓、评分器
  评 B 仓）。修复：repo 与 base_commit 逐字相等断言 + 两个负测试；
  登记 T2-c 义务——resolved-package validator 还须比对 public.image/
  image_manifest_digest 与 T1 键控清单该 instance_id 的记录；消费方按
  digest 取回 bundle 后必须重跑关系验证（不能只信构造时检查）。
严重 2 vendor 路径/命令自声明：spec_vendor_file 接受任意路径（/tmp/attacker.py
  过 schema），叠加"importlib 按路径加载"的计划 = 路径注入 + 命令执行入口。
  修复（采纳其更稳妥方案）：spec_vendor_id 封闭 Literal + envpack/spec_vendor.py
  固定注册表（id → pinned 路径+sha256）；构建期提取规范化 JSON、运行期只读
  JSON；eval_cmd 权威 = derive_eval_cmd(vendor_id, repo_key_lower, version)
  派生，bundle 字段只是信息性副本，verify_grading_eval_cmd 互检（"rm -rf /"
  注入负测试）。
一般 3 provenance 可复现性：source_url 改为含完整 commit sha 的 immutable
  URL；上游 MIT LICENSE 全文入库并登记 digest（不再只留一句 license_note）。
一般 4 机器复算：新增 tests/envpack/test_vendor_specs.py——33 仓库/808 对、
  216/216 覆盖、全小写键、逐 survivor derive_eval_cmd 非空、官方 swebench
  0/216（skipif 无 swe 依赖组）全部变成可重算断言；三个 CLI marker 测试
  （grading v2 / validation-only 默认豁免+强制命中；package 默认与强制都过）。
```
