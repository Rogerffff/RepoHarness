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

## T2-b 修订 2（2026-07-13，codex 轮次 13 → 互检接线 + 打包正确性）

```text
严重 1 互检未接线：verify_grading_eval_cmd 存在但 build_environment_package
  没调用——"rm -rf / #" 的 grading bundle 仍能组出正式包（"权威"只写在注释里）。
  修复：builder 强制互检（构造期第一道防线）+ 新增 build_private_grading_bundle
  （eval_cmd/python_version 由注册表派生，ingestion 不自己填）+
  "恶意命令不能组包"负测试。T2-c/T2-d 的消费期互检义务保持登记。
严重 2 运行期 JSON 不在 wheel 里：spec_vendor 用 parents[4] 推算仓库根，
  codex 实构 wheel 验证 contains_vendor_json=False——安装态必坏。
  修复：JSON 移入包内 envpack/data/、importlib.resources 读取；
  本地重建 wheel 实证 contains_vendor_json=True
  （repoharness2/envpack/data/swegym_specs_242429c1.json）；
  包内资源存在性 + 重提取逐字节等价两个测试钉死。
一般 3 重提取等价：新增测试——digest 锁定的 vendored Python 重新提取后
  必须逐字节等于包内 JSON（防两个 pin 分别更新语义脱节）。
一般 4 provenance 的"importlib 按路径加载"旧措辞已更新为运行期只读 JSON。
```

## T2-c 完成（2026-07-13）：ingestion 构造器 + 真实 216 题构造

`envpack/ingest_swegym_lite.py`（库）+ `experiments/s2_1_ingestion/
build_environment_packages.py`（运行器）。真实构造 **216/216 ALL PASS**，
产物落 `s2/ingest/`（五文件，确定性字节，digest 入 manifest）。

```text
关键落位（历轮登记义务逐条）：
- strip_spec 驱动：11 列双向 fail-closed；家族映射 = 冻结常量 + yaml digest
  pin（运行器核对）+ 语义等价测试（pyyaml importorskip）三保险；
  hints_text/created_at 等 strip/pipeline_meta 字段实测不进任何 bundle。
- D5 survivor 级断言收编为库函数（T1a 原型 → build_task 内断言）。
- 镜像身份：只消费 T1 v4 store（load_state 严格加载 + finish_assertions
  全过才许进入）；public 的 image/digest 逐字来自键控清单条目。
- eval_cmd：全部经 build_private_grading_bundle 注册表派生（轮次 13 定案），
  运行器对 216 条全量跑消费期重验（verify_package_relations：四方 digest/
  身份/镜像身份/eval_cmd 互检——轮次 12 登记的消费期义务的可调用实现）。
- 去重语义：环境身份簇报告 = 2 簇（moto-6469/6470、mypy-11824/11857），
  全部 distinct_tasks_shared_environment、0 suspected_duplicate，
  两对均保留（回归测试锚定）；suspected 只标记进人工复核，永不自动删。
- 泄漏防线：public 面逐条过 scan_public_bundle（0 命中）。
测试：12 项（合成夹具 9 + 真实 216 集成 2 + strip_spec 等价 1）。
产物 digest：
  environment_packages_v0.jsonl  e9de7677…
  public_bundles_v0.jsonl        278a52be…
  grading_bundles_v2_v0.jsonl    762a3ad1…
  validation_bundles_v0.jsonl    196fdf81…
  duplicate_clusters_v0.json     e0b7d2d9…
```

**T2 剩余**：T2-d `grade_controlled_patch` 受控入口 → T2-e 门 runner +
fixture + `EnvValidationReport`。

## T2-c follow-up（2026-07-13，codex 轮次 14 → 可信输入链 + 严格消费链闭合）

四条全部成立并修复（数据内容本身经其核验无误——五文件确定性复建逐字节相等）：

```text
严重 1 输入未对 T1 封板验证：运行器曾"读当前文件现算 SHA 当 provenance"，
  输入被一致修改会被合法化而非报漂移。修复：新建独立封板记录
  t1_input_pins_v1.json（七项输入 digest；不可追加，区别于持续追加的
  s2_1 总 manifest），其自身 sha256 钉死在 envpack/t1_pins.py 常量
  （代码在 S1 账本 rglob 内）→ 代码→pins→输入文件三级防篡改链；
  运行器 provenance 值改为取自 pins（7/7 命中才开工），漂移注入有测试。
严重 2 strict validator 三旁路：vendor digest 不核注册表 / raw+keyed 不核
  pins / image_store 可选忘传即静默跳过 / 消费期无泄漏扫描。修复：
  verify_package_relations 改为 pins+image_store 必传、无条件全查
  （含消费期 scan_public_bundle）；合成夹具用显式命名的
  verify_bundle_relations_non_authoritative，正式 validator 无 None 降级；
  vendor/provenance 篡改各有回归测试。
一般 3 输入面收严：raw 行重复 id 拒绝（不静默覆盖）、全部 230 行先过字段面
  （不只选中 216）、F2P/P2P 内部重复与交集拒绝、fingerprint 复用
  _as_test_list 归一化。
一般 4 输出事务化：五文件原子写 + ingest_manifest_v0.json 提交记录
  （五 digest+行数+T1 pins）最后原子落盘；新增 load_ingest_outputs
  strict loader（提交记录→digest→模型→去重→216 逐包 strict 验证），
  T2-d/e 只许经它消费；运行器带回读自检，篡改数据文件有拒绝测试。
真实产物重建：五数据文件 digest 与上轮逐字节一致（内容零变化）+
  新提交记录 3408bab7…；测试 20 项（本文件）/ 全套 903。
```
