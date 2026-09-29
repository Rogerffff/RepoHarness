# 材料包与阅读边界

本页供协调者。选择表与来源定位在 `batch_manifest.json`；当前本机产物在仓库根 **`runs/swegym_quality_batch01_20260921_v2/`**（git 忽略）。v1 包保留，v2 仅澄清旧公开提示的适用范围；原题/源码/评分材料未改。同工作区的新任务可直接读取。准备材料不等于 12 题质量检查完成。

| 路径 | 内容 | 谁可读 |
| --- | --- | --- |
| `public/<id>/` | 冻结 public bundle、当前函数静态渲染的用户 prompt、中性环境说明、精确 base 的全部 Git 跟踪文件导出。没有 `.git`、未来历史、gold 或新验收补丁。 | 本题公开读者；私有角色也可读。 |
| `private/<id>/` | grading/validation 原始行、test.patch、gold.patch、环境对照引用和原账本/日志定位。 | 私有主审、reviewer、协调者。 |
| `history/<id>/refs.json` | 旧 Claude 记录与 09-20 Codex 记录路径，不复制结论进初始任务卡。 | S3 自主分析保存后才提供；reviewer 初判后才能看。 |
| 本目录 `results/<id>/` | 待各角色写入的审查结果，当前未生成。 | 主审/复核者按派发阶段读取；模型 solver 不读。 |

**可直接复用的本地原件：**`s2/ingest/{public,grading,validation}*jsonl`、`runs/env_overnight_20260916/repos/` 中精确 base 的 Git 对象、09-19 的环境目录与原日志。manifest 逐题记录 JSONL 行号与相对路径。镜像本身不在此包中；本轮不下载 Docker 镜像或依赖。远端已删除也不影响静态复核。

`prepare_materials.py` 只读取 Git 对象和本地文件，**不 checkout、不执行项目代码、不读网上最新修复**。导出不采用 `git archive` 的 export-ignore/export-subst 行为，保持跟踪文件原字节与可执行/符号链接类型；没有子模块时也记录该事实。它会拒绝覆盖已有输出，新的输入另建版本，不回写历史。

当前材料身份和核验结果见 [material_check_v2.json](material_check_v2.json)，[v1 核验](material_check.json)保留：**12 题已打包，36 个来源行对应，9791 个 base 跟踪文件的原始 blob 字节核对，24 条 noop/gold 日志引用和 SHA 对账通过**；所选 base 无子模块、LFS 占位或符号链接。固定抽样可复算，公开目录没有 `.git` 或本次私有材料。准备过程没有运行题目代码。此处校验用于让 review 可复现，不新增训练闸门；材料失配需说明后重建，不等同题目质量差。

## 必须保留的限制

- `user_prompt.txt` 由当前 `render_user_prompt` 生成；**不是捕获的实际模型请求**。public_hints 仍可在 public bundle 读取，但没有冒充 CC system prompt。CC 的自动指令/工具 schema 不在这份静态包，后续真实入口再核。
- base 导出不等于镜像文件树：来源环境提交、未跟踪构建残留、预装包/资产、公开祖先 Git 历史未提供。静态读者可据此提出缺材料；后续 actor 预检回填差异并复核受影响结论，不自行把未来 clone 暴露给它。
- 主审需要追 helper 时可从本题 base 全树读取；不能混用本地 clone 当前 HEAD。共享克隆可能是仅 Git 对象树，工作区状态不是本题初态，禁止 checkout/reset 污染别人。
- 本机各角色具有共享文件系统权限。只发公开路径与新上下文是信息控制约定，不是 OS 隔离；读到私有内容必须记暴露。公开目录中的 base 测试是求解者可见材料，本来就应保留，不能为“盲审”删除。
- 抽样只依据固定的仓库/未复核池与 ID，不保证六道抽样题均为“无问题正常样本”。不能发现新问题就换题或反推全池比例。

## 重建（仅材料丢失时）

在仓库根使用 `rh2/.venv/bin/python <本目录>/prepare_materials.py --output runs/swegym_quality_batch01_20260921_v3`；解释器需要能导入本仓库 RH2 的 `PublicTaskBundle/render_user_prompt`。脚本默认输出 v1，重建应显式给新目录，已有目录不覆盖。manifest/源码若已变化，先说明变化、另存新版本和 material_check，不复写旧核验。

没有必要让每个 agent 读完整外部精读库。协调者按八方面协议追溯 [环境专题](../../../../../harness_improve/external_paper_references/environment_processing_survey_20260915/README.md)；角色卡已给具体检查动作。外部观点与旧调查均是证据线索，不自动批准修题。
