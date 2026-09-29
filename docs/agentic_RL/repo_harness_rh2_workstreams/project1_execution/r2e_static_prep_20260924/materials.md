# R2E 48 题静态筛查材料与阅读边界

2026-09-24 夜，Claude（B 线）。本页供协调者，对应 [static_screening_prep.md](../r2e_env_repair_20260924/static_screening_prep.md) §5 的"固定材料"（SWE-Gym 流程步骤 ①）。材料已准备，静态筛查本身尚未开始；审查者派发需要用户另行确认。准备材料不等于题目质量已检查。

**当前版本是 v3**（09-25 上午）：`runs/r2e_static_prep_20260924/v3/`。摄入面换成 R2E 措辞的公开提示后重新生成，与 v2 只差 48 题的 `public_bundle.json`（`public_hints` 与摘要）和 `environment_brief.md`（"提示与镜像不符"一句改为描述新提示）；私有与历史包不变；verify 48/48 工作树、15/15 镜像一致（`v3/material_check.json`）。首批 8 题按 v2 审，第二批起用 v3。

**v2**：`runs/r2e_static_prep_20260924/v2/`（git 忽略，09-25 生成）。v2 的公开包与 v1 逐字节相同（50,203 项，含子模块空目录），差别只在私有与历史包：v1 的 `private/<iid>/refs.json` 由环境记录生成，早于批次三写回（7 题的配方与材料版本是旧的），还混入了逐题记录、提案等历史结论路径；v2 改为 `run_refs.json`，只列各账本里本题的原始运行行并标明是否属于当前材料版本，历史类路径全部移到 `history/<iid>/refs.json`。`verify` 也按 Codex 批次三复核 F2 改为重算实际文件：v2 核验 48/48 工作树与清单一致、15/15 镜像一致，8 项反例（改字节、增删文件、改软链、改权限、空输入、镜像目录不存在）都按预期报错，见 `runs/r2e_static_prep_20260924/verify_negative_checks.log`。v1 保留作历史，不再给审查者用。核验记录见 [material_check.json](material_check.json)（v1 当时的副本；v2 的在产物目录里）。

| 路径 | 内容 | 谁可读 |
| --- | --- | --- |
| `public/<iid>/` | `public_bundle.json`（冻结的公开面原行）、`user_prompt.txt`（当前 `render_user_prompt` 渲染）、`environment_brief.md`（中性环境说明）、**`worktree/`（实际解题工作树）** 与 `worktree_manifest.json` | 本题公开读者；私有角色也可读 |
| `private/<iid>/` | 当前生效的 `hidden_tests/`（含修订）、`expected_output.json`（含修订）、`gold.patch`、`run_tests.sh`、评分面 / 验证面原行、本题修订单条目 `revisions.json`、`run_refs.json`（v2：只有原始运行行，标出当前材料版本；v1 是 `refs.json`，已停用） | 私有主审、复核者、协调者 |
| `history/<iid>/refs.json` | 本轮逐题记录、findings 与材料修订提案的路径（不复制结论） | 主审自己的分析保存后才提供；复核者初判后才能看 |

## 实际解题工作树怎么来的

公开包给的是解题者在 `/testbed` 实际看到的初始工作树，不是上游提交树（Codex 批次二复核 F2）。取法：

1. base 提交的跟踪文件：从上游仓库按提交浅取，用 `ls-tree` + `cat-file` 读原始 blob 字节，逐个核 blob sha1，保留可执行位与软链。不 checkout，也不用 `git archive`（它的 export-subst 会改写 pandas 的 `_version.py`）。子模块只记提交号、导出为空目录，镜像里同样是空目录。
2. 镜像初态相对 base 的改动：叠加 M3 在镜像内取得的 `git diff HEAD`（`runs/env_overnight_20260916/M3/facts/<commit12>/facts/initial.diff`）。12 题非空：pandas 7 题（删除 `pyproject.toml`，修改 `pandas/__init__.py`、`pandas/_version.py`、`setup.cfg`、`versioneer.py`）、aiohttp `1c1c0ea3` `22a12cc2` `4075c653`（`Makefile`）、`240da100`（3 个源文件）、`61833518`（4 个源文件）。全部干净应用，删除项保留为删除。
3. 未跟踪的构建文件：`run_tests.sh` 取评分面原文（摘要与镜像事实一致）；`install.sh`、orange3 的 `datasets` 软链、aiohttp 的 `process_aiohttp_updateasyncio.py` 只在镜像里，从手上的镜像拷出。
4. 不导出：`.git`、被 `.gitignore` 忽略的构建产物（编译扩展、`.venv` 等）、隐藏测试。

## 核验结果

| 项目 | 结果 |
| --- | --- |
| 跟踪文件 | 48 题共 49,932 个，逐个核过 blob 字节 |
| 初始差异 | 12 题全部干净应用，应用后文件的有无与差异声明一致 |
| 私有包隐藏测试 | 120 个文件逐个与评分面摘要相同（代码取来源行原文并重放文本修订，`__init__.py` / `helper.py` 取 M3 镜像副本，新增文件取修订单文件） |
| 镜像逐文件比对 | 15 张镜像全部一致：pandas 7 题、aiohttp `1c1c0ea3`、`240da100`、`61833518`（覆盖三类脏树）与 coveragepy `016af5f6`、datalad `58ba5165`、numpy `43e333e2`、orange3 `9b5494e2`、scrapy `cfed9b66`。比对范围是镜像里 `git ls-files -c -o --exclude-standard` 列出的全部路径；镜像 HEAD 都等于本题 base |
| 权限差异 | 每题 2 到 4 个文件镜像里是 0664、导出是 0644：镜像构建时写入的 `install.sh`、`run_tests.sh`、`process_aiohttp_updateasyncio.py` 与 aiohttp 的 `Makefile`。内容逐字节相同，静态审查不受影响 |

aiohttp `240da100`、`61833518` 两张来源镜像是这次为核对第三类脏树按摘要拉取的，其余 13 张是已有镜像（派生镜像，解题者视角）。

## 必须保留的限制

- **33 题缺 `install.sh`**（没有镜像）：orange3 另 6 题还缺 `datasets` 软链，aiohttp `22a12cc2`、`4075c653` 还缺 `process_aiohttp_updateasyncio.py`；缺什么逐题写在 `worktree_manifest.json` 的 `untracked_missing`。已观察到的同仓库 `install.sh` 逐字节相同（aiohttp 3 题、pandas 7 题），其它仓库各只看到一题；缺的文件不据此补。
- 没有镜像的 33 题，工作树由同一方法得出，但没有逐文件比对；其中 aiohttp `22a12cc2`、`4075c653` 属于已核对过的 `Makefile` 类。
- `user_prompt.txt` 是当前函数的渲染结果，不是捕获的实际模型请求。`public_hints` 里 conda / pip 的说法对 R2E 不成立，中性说明已写明。
- 中性说明只写环境事实（解释器版本、有无 pip、无出网、导入与 `python -m pytest` 要求、xvfb、git 身份、环境配方固定的包版本），不引用逐题记录里的证据链：`solver_conditions` 的备注有时提到期望键，不能进公开包。
- 各角色在同一文件系统上。只发公开路径是信息控制约定，不是系统隔离；读到私有内容必须记暴露。

## 重建（只在材料丢失时）

从仓库根运行：

```
rh2/.venv/bin/python <本目录>/prepare_materials_r2e.py fetch                     # 联网，按提交浅取 48 个 base
rh2/.venv/bin/python <本目录>/prepare_materials_r2e.py image-hashes --image <iid>=<镜像> … --out <目录>   # 有 Docker 的机器
rh2/.venv/bin/python <本目录>/prepare_materials_r2e.py prepare --out runs/r2e_static_prep_20260924/v2
rh2/.venv/bin/python <本目录>/prepare_materials_r2e.py verify  --out runs/r2e_static_prep_20260924/v2
```

`prepare` 不覆盖已有目录；输入（摄入面、修订单、M3 事实）变化时另建新版本并重做核验，不改写本版记录。
