# Pandas 50319 R13 正式六候选矩阵与收尾原件独立窄核（2026-10-03）

结论：**本次冻结 R13 下的 50319 正式 CPU 六候选对照及作业收尾，在所核范围内通过，未发现阻断。** 原 manager reward 依次为 `0/1/1/0/0/0`；Gold 与局部 `None` 回退均满足两条新增 F2P（失败转通过）及全部 109 条来源 P2P（原已通过测试保留）。恒 `None` 被 36 条来源 P2P 拒绝，错误格式被两条新增 F2P 拒绝，只修 reported 示例的候选仅通过一条新增 F2P。各臂都有真实扩展编译、链接、复制及正确身份导入，缺席、skip 和重复节点均为 0；候选、CLI、矩阵和外层作业正常收尾。作业结束后的 18 条精确查询证明本次六个 run 标签的容器/网络及六个确切 grader 名字在读取时无残留。

该结论限定本题、本 job、R13 材料、六份输入和实际预算。普通 source 路径的六行 `image_id_actual=null` 原样保留；额外 Docker inspect 只直接证明末臂的实际镜像 ID。**本报告不认定真实模型求解、probe、全角色链或训练资格完成。**

## 核查角色、接触上下文与执行边界

核查者为本包非作者 subagent，没有编写本轮材料、候选、包装器或执行 CPU 作业。已接触题主提供的路径、版本、结果主张、先前审查和 canonical Gold 漏收后的补读，因此不是盲审；作者摘要只作待检验主张。结论根据原命令、正式 prepare 文件、冻结 payload、完整日志、账本、诊断、作业状态及逐查询输出独立形成。

限定复用同目录三份既有报告：

- `non_author_material_review_20261003.md`，SHA256 `8d166cbc274830eb16c7f4b0429fc62afa623b960bd3eb2c9e4f65bc058e912a`：原静态材料范围按已核版本复用。
- `non_author_cpu_evidence_review_20261003.md`，SHA256 `4fe58964c2191990ee4cd387f3f284fc1f5801c48242338f33bd9efcb1ea67e6`：原 CPU 镜像资产及 50319 root 私有 NoOp/None 校准。那次私有 pytest 没有本次正式 manager reward。
- `non_author_50319_public_actor_review_20261003.md`，SHA256 `b9eaca5489694469a9056676d6dc5d868d4a63e748df0279af43ae984bc96222`：原 R5/runtime_cpu_v2 公开 actor 的模型桩开发链。它不改写为 R13 actor，也不支持真实模型求解结论。

已核 V3 冷输入的角色、资格输入、cleanup 字段及协作取消范围限定复用；本轮只补实际结果与收尾，没有重做全题静态、旧 None 校准、旧公开 actor、48106 或整个 1094 文件发布审计。本机动作仅为只读文件、SHA/字节重算、JSON/文本解析、内存统一补丁应用、base64 解码和逐来源/成员对照。没有 SSH、Docker、联网、安装、项目代码导入执行或新实验；下文 SSH/Docker 的 rc 均来自题主取回的原件。唯一写入是排他新建本报告；旧报告、共享代码、输入、作者材料和总账未修改。

## 原件完整性与正式消费身份

主原件根目录（以下记为 R）：`runs/category2_repair_20260929/pandas_cpu_20261003/formal_r13_50319_received_whole_v1/`。独立重算 `receipt_manifest.json` 的 SHA256 为 `ee180c751b3432bd336be3d2352ac7a99af19c3fc576feac5fbb0315e9f36e52`；其 127 件合计 7,430,507 字节逐项均一致。该 receipt 覆盖整个已完成矩阵，不把其他题或旧原件混入数量。

`R/inputs/input_manifest.json` 为固定 V3 的同一字节，SHA256 `1f998778711889e91fc0954b61367be2985dfafd447f01c3fc0bf83f604a0530`。主归档最初缺其明列的 `gold/pandas-dev__pandas-50319.gold.patch`，其余 11 项均直接核同固定 V3；漏收项已由独立远端只读原件补齐，主 receipt 未回写：

- `formal_50319_canonical_gold_supplement_20261003_v1/receipt_manifest.json`，SHA256 `f948e05afeee332c67356e75bca61ef4b74176e1710266cb295d00dbce937e9c`。
- 该目录 `raw_transport_stdout.json`，1,214 字节，SHA256 `c05f17bc391c071d5b7960044c87126311d8de889ac2946ec2d90ca1cdae4602`：保存远端确切 canonical 路径、709 字节、SHA 与 base64。独立解码等于该目录正文、固定 V3 canonical 副本、R 的 `inputs/gold.patch` 及原 validation Gold 字节。
- 原脚本 `runs/category2_repair_20260929/pandas_cpu_20261003/read_50319_canonical_gold_cpu_c_v1.sh`，459 字节，SHA256 `da0ec9b7153f065d1c7a50cad3e477f10e76d680162f620298f8da174f4f2ab0`；补读 receipt 内原包装器 `rc=0/stderr=''` 与脚本/raw stdout 摘要吻合。

因此 12 项固定输入可闭合，漏收是已补齐的归档缺项，没有据副本名称臆测远端 Gold 角色。

实际 prepare、各 arm command、job/status 均指向 `cat2-cpu-r2e089092-swe27-pandas-moto-20261003-v1` 的冻结 CLI 与 `runtime_cpu_v2`。本机发布根为 `runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe27_pandas_moto_v1/`；`manifest.json` SHA256 `3fad18daff8db219294e10cbf08d4424d68cf7000d008bb983cba4bdc427b641`。只对本轮实际消费的 CLI、replay、manager、prepared_task_face、scoring、pandas50319_revision 以及三份 producer 输入重核 manifest 条目，均吻合。

正式 `R/prepared/prepared_manifest.json` SHA256 `ab4b975e930953b00e27031abb6cbbe2a9a5abbe0d36d7888e694ccfeefdf543`；其中两份公开文件的 SHA/行数、单任务身份和 `R/private/host_grading_views.jsonl` 的 SHA256 `e143109b0ec0087ae4621e14effdf50cc5ecd8591c14397936ca8b5e4511619a` 均独立吻合。prepare 原命令 rc0。公开 view 与原公开 bundle、冻结 producer 字段相等；host grading 与冻结 producer 相等，以下 canonical digest 独立重算一致：

| 身份 | 实际摘要 |
| --- | --- |
| revision | `pandas50319-dot-date-full-bindings-v1` |
| 原 grading 父 | `sha256:d37caa1d070ef67c1487e31485f8a5463d81761393acd88294aeaf99cc9ee17d` |
| 原公开 bundle | `sha256:5c94214a75aca9417902ae115febdacf58f52a1a9a5f553631234c67832a7d27` |
| 本修订 grading | `sha256:052e12f6f141684685ac704a3efc3fd40e686f1f6f18a85edcefef3d7feefcc3` |
| environment package | `sha256:b2cc52ce26461d7970ffedbf3077e2908a3b91c4dddfc7c23d5b6cc115e2e6b5` |
| 本次材料身份 | `sha256:aec98b708135a7f293dc888a0a4cf70090584a6ea40fd1a32f0f087aac652979` |
| 完整绑定 | `sha256:d2d78ebe7df4115b4d2d8e748fd83ff54e68c3234b3d91c814bff65c468097cd` |
| source 镜像身份/期望 manifest | `sha256:e645e4346df9200174e8b879ad8fb7a09f64f91c7375311e2569596d054ba21e` |

这里保持原 `eval_cmd=pytest -rA --tb=long`、vendor `swegym_constants_242429c1`、base `1613f26ff0ec75e30828996fd9ec3f9dd5119ca6`、109 条来源 P2P 的顺序与内容；schema 按登记修订升级，F2P 和有效测试补丁按修订替换。原公开问题/权限没有发生本轮改写。实际 parser/grader 为 `swebench-4.1.0+swegym_parsers@242429c1+pandas50319-dot-date-full-bindings-v1`，rollout UID54321、grader UID54322、2 CPU/4 GiB/pids512/deny_all 等 profile 与正式输入和六行 policy 相同。

## 六份实际候选与扩展构建

独立把五份补丁应用于原公开 base 的 `pandas/_libs/tslibs/parsing.pyx`，只在内存处理；NoOp 不改 base。每份结果均逐字等于其冻结 payload，并等于候选身份观测的 source SHA。NoOp frozen entries 为空；其他臂均只有这一个 regular `100644/modify` 文件，未触及测试/fixture/conftest，`excluded_pathset_changed=false`，无额外 overlay。各 frozen artifact 的公开 digest、runtime manifest 和 HEAD 与正式输入一致。

Gold canonical 补丁为 709 字节，SHA256 `70ca3fa70b50975e2fe34f0f790e66f9f7c7a1453220c0bf6d69d30d145214ec`，实际 `kind=gold/gold-dir`。四个 controls 实际 `kind=cc/patch`，不把手工补丁重标为模型 actor 或 Gold。

| 臂 | 实际 source SHA256 | 实际加载扩展 SHA256 |
| --- | --- | --- |
| `noop` | `5c8e81b9914bc6448b21a909cf13d3c2e7799e63e92d386042dd4262b6d048aa` | `127481b230a3c52c886aea1d01b8957e61b55ab106e315f93c4a8f399ecd425c` |
| `gold` | `ea2c0d7a5fbec68b265d43bade8a4d02bf4863368928a8be9e9bd77345aa3227` | `34853b35871461234ef14b2a9cfc83ca8a9090fbdbb5f831cdb7a3d6e42eb8ea` |
| `none_fallback` | `54262be7b7f417a620f4f15e8703453bc703652a8e4001a0d1e8f8cca594a8ca` | `f1a4317cf944fc215e6253ed723ba78e30acbddb3e5d574a2b0b784c326a1ad4` |
| `constant_none` | `baa06e68aa61f71f13cb044480c88011acec2160038d53178e7d5f4628fabaaa` | `eb297a39e9896c4c17e55944ccbdecfadd2fd09ded7db09ecbb8c17fb30eaf71` |
| `bad_format` | `c9d69582dfb22ed35cc14530613cf7e51358c60f48be9376698af58ffe913476` | `8a5600a6da04b8aebe7a909a0efb7555570efdbf203bd35b51954e36421dcaf1` |
| `reported_only_none` | `019d0e80aa34cf59270138806ad8600d40779bd68d2b0480345386dce78c0fae` | `c7a43c72edfdc978e679d4ccf3cc3b7889e63810ec38d9b2202e105617170bee` |

源码以 R 内相应 `artifacts/.../frozen_patch.json` 及 `inputs/*.patch` 为原件；observations 以相应完整 `.diagnostics.json` 为原件，账本记录相等。五个改源码的臂均有 `Cythonizing pandas/_libs/tslibs/parsing.pyx`；NoOp 没有这条重新 Cython 化记录，但确有从镜像原 C 文件重新 compile、link 与 copy 扩展的日志。不得把 NoOp 原源码/扩展 SHA 未变化说成没有编译，亦不得声称其扩展 SHA 改变。

实际安装串逐字为：

```bash
python -m pip install 'numpy<2'; python -m pip install -ve . --no-build-isolation -Ceditable-verbose=true; pip uninstall pytest-qt -y;
```

六份原日志均有 editable build `finished with status 'done'`、`Successfully built pandas`、`Successfully installed pandas...`，没有实际 `RH2_INSTALL_CMD_FAILED=` 行；`RH2_INSTALL_RC=0` 与账本 install 相同。该 rc 是整串最后一条命令的 rc，单独不能证明前面的构建成功；本判断同时依据真实 compile/link/copy 和 pip 成功记录。下表编译行号是相应 R 下原 `.eval.log` 的一基行号，时间均为原 epoch 秒。

| 臂 | Cython / compile / link / copy 行 | install start → extension mtime → install end | install 秒 / rc | test 秒 / rc |
| --- | --- | --- | --- | --- |
| `noop` | 无 / 3853 / 3858 / 3992 | 1790984430.690966677 → 1790984998 → 1790985109.657538170 | 678.967 / 0 | 6.006 / 1 |
| `gold` | 3167 / 3877 / 3882 / 4016 | 1790985787.301797521 → 1790986358 → 1790986477.786999622 | 690.485 / 0 | 6.487 / 0 |
| `none_fallback` | 3166 / 3876 / 3881 / 4015 | 1790987101.606344514 → 1790987662 → 1790987767.812522049 | 666.206 / 0 | 5.951 / 0 |
| `constant_none` | 3163 / 3874 / 3886 / 4020 | 1790988416.635020196 → 1790988959 → 1790989077.735505979 | 661.100 / 0 | 5.944 / 1 |
| `bad_format` | 3166 / 3876 / 3881 / 4015 | 1790989703.589671500 → 1790990277 → 1790990389.685254341 | 686.096 / 0 | 4.848 / 1 |
| `reported_only_none` | 3168 / 3878 / 3883 / 4017 | 1790991008.220149939 → 1790991588 → 1790991695.444186535 | 687.224 / 0 | 5.170 / 1 |

每臂扩展 mtime 均严格晚于其本次 install start、早于 install end，随后独立启动的 post-observation Python 实际加载 `/testbed/pandas/_libs/tslibs/parsing.cpython-38-x86_64-linux-gnu.so`。六臂实际 `os.geteuid()==54322`、`sys.executable=/opt/miniconda3/envs/testbed/bin/python`、`pd.__file__=/testbed/pandas/__init__.py`、`identity_ok=true`；路径检查/源码 SHA 检查在本臂 helper 中明确执行。版本为 `2.0.0.dev0+940.g1613f26ff0.dirty`。完整身份 JSON 位于 NoOp/Gold/None/bad_format 诊断第 338 行、constant_none/reported_only_none 第 339 行。

这些后观测是候选身份的私有诊断，manager 不据它们改 reward；本报告对六份已固定、可逐字检查的候选使用它们核导入身份与调用者，未声称它们能提供任意恶意候选的通用可信证明。

## 新 F2P、全部来源 P2P 与完整成员

正式有效测试补丁 SHA256 `0cef8c604fb79cd8d677087b28a09736751617e5aacfb312cb8fede48d3cae8f`，与 R13 grading、plan、revision metadata 相等。原单例补丁 SHA256 `fbd09c78ef472b070a1a27cea70da3ed0965c19626913bf17175fc50a0a1be97` 留作来源；正式 trusted setup 仅含有效补丁一次，原补丁零次。各臂先从固定 base 恢复 `test_parsing.py`，实际 baseline SHA 为 `71a22bdd98579e54c45342f8d3e1d80658ba155ad9be64ac34659f976253ff4d`，与原 base 文件 10,706 字节一致，再应用补丁。root 自证每臂 `RESTORED=1/APPLY_RC=0/ABSENT=0/OK=1`；没有叠加旧 F2P 测试。

我直接解析各原 pytest `-rA` 完整状态行，不使用作者计数或仅按截断前缀认通过。每臂恰有 115 个唯一完整节点：两条新 F2P 加 113 个来源 P2P 实际节点；109 条来源 P2P 由 94 条精确节点、12 条唯一旧截断映射、三组显式绑定组成，组大小 1、2、4，全部来源均有状态。七个成员未被聚合状态掩盖。每臂 missing/ambiguous/duplicate/skip/xfail/xpass/error 都为 0，账本 `reference_missing_count=0` 相符。

| 臂 | 新 F2P 通过 / 2 | 来源 P2P 失败 / 109 | 全部物理节点通过 / 失败 | 正式 reward / outcome / failure_category |
| --- | --- | --- | --- | --- |
| `noop` | 0 / 2 | 0 / 109 | 113 / 2 | 0 / `unresolved` / `tests_failed` |
| `gold` | 2 / 2 | 0 / 109 | 115 / 0 | 1 / `resolved` / `null` |
| `none_fallback` | 2 / 2 | 0 / 109 | 115 / 0 | 1 / `resolved` / `null` |
| `constant_none` | 2 / 2 | 36 / 109 | 75 / 40 | 0 / `unresolved` / `tests_failed` |
| `bad_format` | 0 / 2 | 0 / 109 | 113 / 2 | 0 / `unresolved` / `tests_failed` |
| `reported_only_none` | 1 / 2 | 0 / 109 | 114 / 1 | 0 / `unresolved` / `tests_failed` |

上述失败均为真实 `tests_failed`；没有把 infra、缺席或安装失败算成预期零分。下两表的数字均是对应原 eval.log 行号，统一完整节点前缀为 `pandas/tests/tslibs/test_parsing.py::`。

| 新 F2P 完整节点（前缀之后） | NoOp | Gold | None fallback | constant None | bad format | reported only |
| --- | --- | --- | --- | --- | --- | --- |
| `test_guess_datetime_format_dot_date_contract[reported]` | FAILED / 5110 | PASSED / 5017 | PASSED / 5011 | PASSED / 6576 | FAILED / 5236 | PASSED / 5054 |
| `test_guess_datetime_format_dot_date_contract[another-dot-date]` | FAILED / 5111 | PASSED / 5018 | PASSED / 5012 | PASSED / 6577 | FAILED / 5237 | FAILED / 5104 |

| 组 | 完整绑定成员（前缀之后） | NoOp | Gold | None fallback | constant None | bad format | reported only |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `test_is_iso_format[%Y\\%m\\%d %H:%M:%S-True]` | PASSED / 5092 | PASSED / 5050 | PASSED / 5044 | PASSED / 6592 | PASSED / 5218 | PASSED / 5086 |
| 2 | `test_guess_datetime_format_with_parseable_formats[2011-12-30 00:00:00-%Y-%m-%d %H:%M:%S]` | PASSED / 5034 | PASSED / 4990 | PASSED / 4984 | FAILED / 6612 | PASSED / 5160 | PASSED / 5027 |
| 2 | `test_guess_datetime_format_with_parseable_formats[2011-12-30 00:00:00.000000-%Y-%m-%d %H:%M:%S.%f]` | PASSED / 5058 | PASSED / 5014 | PASSED / 5008 | FAILED / 6624 | PASSED / 5184 | PASSED / 5051 |
| 3 | `test_guess_datetime_format_no_padding[2011-1-1 00:00:00-%Y-%d-%m %H:%M:%S-True-None]` | PASSED / 5087 | PASSED / 5045 | PASSED / 5039 | FAILED / 6643 | PASSED / 5213 | PASSED / 5081 |
| 3 | `test_guess_datetime_format_no_padding[2011-1-1 00:00:00-%Y-%m-%d %H:%M:%S-False-None]` | PASSED / 5086 | PASSED / 5044 | PASSED / 5038 | FAILED / 6642 | PASSED / 5212 | PASSED / 5080 |
| 3 | `test_guess_datetime_format_no_padding[2011-1-1 0:0:0-%Y-%d-%m %H:%M:%S-True-None]` | PASSED / 5083 | PASSED / 5041 | PASSED / 5035 | FAILED / 6639 | PASSED / 5209 | PASSED / 5077 |
| 3 | `test_guess_datetime_format_no_padding[2011-1-1 0:0:0-%Y-%m-%d %H:%M:%S-False-None]` | PASSED / 5082 | PASSED / 5040 | PASSED / 5034 | FAILED / 6638 | PASSED / 5208 | PASSED / 5076 |

恒 None 的 **36 是来源引用失败数，40 是完整物理节点失败数**：两组失败绑定以 2、4 个成员展开，不能混淆分母。ISO 组那个成员仍通过。恒 None 破坏原成功格式推断，原日志第 4985 行等实际断言 `None == '%Y%m%d'` 失败；两个原 dayfirst 节点也失败（6627–6628 行）。原 wrong-type 两节点仍通过（6586–6587），这不足以挽回正式 reward。

其他五臂 109 条来源 P2P 全保留，包含两个旧 dayfirst、两个 wrong-type，以及成功格式、fractional second/no-padding、locale、quarter 等原来源行为。逐一核对的 dayfirst/wrong-type 四节点行号按两组分别为：NoOp 5061/5062、5074/5075；Gold 5019/5020、5032/5033；None 5013/5014、5026/5027；bad_format 5187/5188、5200/5201；reported_only 5055/5056、5068/5069，全部 PASSED。

NoOp 两例是真实 `_fill_token` 的 `int('')` ValueError（4943、4979 行）。bad_format 两例实际返回 `%Y-%m-%d`，新测试按 `datetime.strptime` 检查时格式不匹配 ValueError（5018、5106 行）。reported_only 的另一例仍为 ValueError（4973 行）；没有仅凭示例修复或整体数组成功就给它满分。

None 回退两次 `guess_datetime_format` 均实际返回 JSON null，原调用者 `pd.to_datetime(inputs, dayfirst=True)` 得到 `2003-03-27T14:55:00` 与 `2004-04-28T16:07:08.123456`，保留非零微秒；其私有观测有 dateutil fallback warning。Gold 返回正确 `%d.%m.%Y %H:%M:%S.%f` 且数组相同、无 warning。恒 None 的数组同样正确，reported_only 的整体数组也正确但第二条直接 guess 仍失败，说明私有数组观测不能替代正式合同和旧行为保留测试。以上调用者观察未加入评分测试、未改变分数。

## 评分脚本、保护与正式环境资格消费

从原 production trusted setup、candidate_test 以及冻结模板重构完整 eval 脚本，只在内存按 manager 规则逐段 UTF-8 加 NUL 重算，得到共同摘要 `sha256:38c1676d0dc7faacf71684b51a62dfc386cfa31cd906964ab75e58ff792939c4`。重构完整 eval 为 3,213 字节，SHA256 `5596cb7016826282699c1cef006fed0be6083702770679ae2e51ece61cd18345`。这与正式 input_identity、六行 ledger、六份 diagnostics、六份 audit/scope 前后摘要全部相等。本次没有 supply/two-stage 或 candidate prerequisite 启用，不额外计算未使用域。

六份 root trusted setup 自证、control surface 保护均真实成功；诊断第 25 行起各为 `RH2_PROTECT_OK=1/EXPECTED_FILES=1/PROTECTED_FILES=1/PROTECTED_DIRS=4/MISSING_FILES_COUNT=0`。六臂 install prefix owner 观测为 54322，runner 前后共同摘要 `1cfac6828a8ce1101528108a0a3379da1fe8e2b0ba4a9021ea32c5ffc26e13a4` 相同，`runner_integrity_changed=false`。候选没有测试路径或 fixture/conftest 改动，正式测试先恢复、核固定 base 后由 root 应用有效补丁，评分运行器和受保护控制面没有本轮候选替换。

包装器实际只把 `env_reset_timeout_seconds` 从 300 提到 900 秒，并追加有 `timeout -k 5 60` 的私有后观测；测试 timeout 1800 秒不变。六臂预算为 candidate stage 1800、grading deadline 3600、cleanup 120、image pull 1800 秒，均为 repeat1 顺序运行；出错停止逻辑保持在固定 V3。这里的 900 秒覆盖实际 CPU 准备/恢复/观测预算，不是评分命令或参考放宽。脚本摘要不覆盖预算与私有 observation，故报告同时明确这两个改变。所有臂自然完成，未测试或承诺外部强杀的收尾保证。

资格消费独立按冻结 `load_env_qualifications` 规则核实际原行：kind 仅接受 noop/gold，报告须 resolved/unresolved、category null/tests_failed，missing0，镜像/脚本身份存在；材料身份参与 manager 匹配。本轮两行都符合，安装真实成功。

| 消费臂 | 原 command 的资格输入 | 原 stdout 加载数 | 实际 ledger/diagnostics 的资格来源 |
| --- | --- | --- | --- |
| NoOp | 无 | 0 | `absent`：没有先前资格输入 |
| Gold（真实 kind=gold） | NoOp ledger | 1 | `ok:ledger.jsonl:rpt_grading_be62478a` |
| None/constant/bad/reported controls | 顺序 NoOp + Gold ledger | 每臂 1 | `ok:ledger.jsonl:rpt_grading_a29b64e6` |

两份输入为同一 task，后读 Gold 覆盖 NoOp，因此后四臂是一个 task 的一份实际 Gold 资格，不是加载数量 2。共同 image identity `e645…ba21e`、scripts `38c1…939c4`、materials `aec9…52979` 和 missing0 均相等；没有拿旧私有校准、旧 actor 或 cc controls 作为资格来源。

## 镜像观察限制、候选/CLI/作业收尾

六行 ledger 和 matrix_state 的 `image_id_actual` 均为 JSON null。这是 frozen 普通 source 路径的真实记录，不能补写成 actual CPU ID，也不以 R 的单份镜像 inspect 证明每个历史容器的实际 ID。

单独补读 `runs/category2_repair_20260929/pandas_cpu_20261003/formal_50319_last_arm_actual_image_20261003_v1.json`：3,012 字节，SHA256 `264a1da0ea22edc473c12ba423f1e5571aaf919eeb3e90323d261fd94050e8b6`。01:38:09 UTC 对末臂精确 run-label 列得 `da9c66d457a7` 后实际 inspect，两个原 rc 都为 0；parsed 等于原 stdout JSON，label 和 diagnostics 的完整 grader trajectory `...reported_only_none-pandas-dev__pandas-50319-a1-5a6f5593` 相等，实际 Image 为 `sha256:a3f20f616f78963bee9c87426b8a93c28fb63a6ade97d0f444115279c28f859a`。该臂资源为 2 CPU、4 GiB、pids512、NetworkMode none。它只直接补证这一臂，不补证先前五臂实际 ID。R 的 `grader_image_inspect.json` 同时显示该 config ID 的 RepoDigest 为已固定 `e645…ba21e`。

每臂独立原 `ledger.cleanup={removed:true,detail:'',steps:['rm:ok']}`；各 CLI stdout 的 manager_close 均累计 created1/removed1、`containers_open=[]/supply_open=[]/cleanup_failures=[]`，final_status 为 `exit_code=0/reason=ok/grader_containers_open=[]/cleanup_failures_total=0`，halted/aborted 均 null。六个 arm command 都 rc0、repeat1、时间不重叠；实际测试失败臂也正常完成报告和清理，不是通过 driver rc 给测试判成功。V3 的 matrix_state 从正确 `ledger.cleanup` 字段读取，所有六行与原 ledger 相等。

`R/job/status.json`（SHA256 `a9a82b5eee798f980d6153da9b8a1472fbb6d28ba76ea36dd5b919532e0ab9c4`）实际 job `pandas50319-formal-r13-v3-2f897642547c` 于 2026-10-02 23:29:36 UTC 启动，2026-10-03 01:41:52 UTC finished/returncode0。`R/inputs/matrix_launcher_result.json`（SHA256 `51dcd105c1192b235eb64295ef64d8a825188f6acc1180c90dc2482c824de2b7`）exit0，完成时间 01:41:52.964656 UTC；launcher.exit 原值 0。

最终现场补读位于 `runs/category2_repair_20260929/pandas_cpu_20261003/`：

| 原件 | 字节 | 独立重算 SHA256 |
| --- | --- | --- |
| `formal_50319_final_residue_readback_20261003_v1.json` | 4,850 | `4a78bbaa0df3d63b53657b521ccb43712f488c6c3ea739b8e11e5baa4ef7dd56` |
| `formal_50319_final_residue_transport_20261003_v1.json` | 688 | `389646b5f01a753be70ec6f79e094fb8fca17a9722d400d660b328937d03f325` |
| `residue_formal_50319_r13_cpu_c_v1.sh` | 1,939 | `7cf50a69fffeaf81cefb8f292cac1e69506faafabdfe0a2b61e33498cccf99e9` |

原脚本只读确切 job 的六臂 labels 和六个 grader 名字，无删除、无全机清理。独立从六行 ledger 的 run_id/report_id 与 frozen 命名规则重建 18 条 argv，与 raw queries 顺序逐字相等；其 canonical query_spec SHA256 `f6e662b89248a80b9442887012a82c3a116a9d4fe7b92008e62e22f636ffe03e` 一致。12 条分别为六臂 `docker ps -a` / `docker network ls` 的精确 `rh2.run_id` label；另六条 `docker ps -a` 的 name 过滤均为首尾锚定全名，后缀分别是 `be62478a/a29b64e6/b741da82/2f25fc5f/d38f2296/ba9196b2`。

18 条原记录时间为 01:49:19.221512–01:49:20.019648 UTC，全晚于自然结束，均 `rc=0/stdout=''/stderr=''`；transport wrapper0/stderr空，script/raw stdout 引用的 SHA 独立相等。因此可以认定**本次 job 在该读取时间的六个 exact run 标签容器/网络及六个 exact grader 名字零残留**，没有靠摘要布尔值独自判定。此结论不扩展到全主机、其他任务、所有文件/进程或未来时刻。

## 核查结论和保留限制

已验证：固定 V3/R13 输入与 prepare/材料身份、实际六候选 source/frozen delta、六次安装与新扩展导入、115 完整节点及 109 来源保留范围、七个绑定成员、正式 reward/资格消费、脚本和 runner 保护、candidate/CLI/矩阵/job 正常收尾，以及 18 条本次精确残留原查询。canonical Gold 漏收已以独立补读闭合；主 receipt 与历史结果没有改写。所核范围无待补阻断。

保留限制：先前五臂没有单容器 actual image ID 直接 inspect，六行 null 仍是 null；后观测只为固定候选的私有诊断，不能替代正式评分；900 秒执行预算和自然完成的收尾不能推成外部强杀保证；旧公开 actor 只在其原版本支持模型桩开发链。本轮没有真实模型求解或训练资格证据。该 CPU 原件结论不自动授予未核的全角色准入或训练用途。

## 逐臂最小原件索引

以下路径均相对 R；每臂的 ledger、frozen_patch、diagnostics、command/stdout、audit 原件已经纳入上述 127 件逐项 hash 核对。日志及账本独立摘要如下，便于定位正式分数和逐节点原状态：

| 臂 | 原 eval.log 路径 | 日志 SHA256 | ledger.jsonl SHA256 |
| --- | --- | --- | --- |
| `noop` | `noop/eval_logs/evallog_replay-pandas50319-forma_be62478a.eval.log` | `4143137e64c5249d3be7ec779c2baf5303c4f77bd0be3a4bbf77590a894b2de9` | `0a8e3a40dae0d84ba17f9cae034994798a5cfa15cbc15c82d824d862813ff910` |
| `gold` | `gold/eval_logs/evallog_replay-pandas50319-forma_a29b64e6.eval.log` | `c6ab20ff511a334bdd9593388f92c6dfb00506b6bc23c152a25c8b542a8b135e` | `137eff363b4b7d4c5ab2a71e55c969427f9f213174ce1c5715ea4287d160ddd8` |
| `none_fallback` | `none_fallback/eval_logs/evallog_replay-pandas50319-forma_b741da82.eval.log` | `6c9f3992554de1fb33112ddbb607a6d4b32de604651fe6e534dbf91afe2af093` | `1782dba61a94c964bfa24ad0d73ef37783120f8602f6c40c1323684c92b91440` |
| `constant_none` | `constant_none/eval_logs/evallog_replay-pandas50319-forma_2f25fc5f.eval.log` | `0127accc80341daf7dc389609353ef06f61564eb850effd17d369f6041f8e642` | `25f62b034c59f73db265ae8b8aa06ed12098d76e03ac39e36d7ca97adb63353f` |
| `bad_format` | `bad_format/eval_logs/evallog_replay-pandas50319-forma_d38f2296.eval.log` | `8d3ad826b87ed878768516417a6cf8e09f9b5cfe803094f18dfeda13289495c0` | `c2bab5bdb2250df916fef5486da92afd7da79011ed74e48be2fa93d183a8e2ba` |
| `reported_only_none` | `reported_only_none/eval_logs/evallog_replay-pandas50319-forma_ba9196b2.eval.log` | `86bea26cfdb72f9dd970a8881dba8a887b261935e4ca5854fc90f634ed89cbcc` | `75c448ee7b22f2c8cc52df31fe7997de70da246ae9e964a93ad3353ac0fed6e3` |
