# dask__dask-7138 — history 前独立主审

主审：pack07_dask。needs_review / static_review；development_diagnostic。新增测试与 array_like 目标基本一致，历史目标失败确为输入无 reshape；gold 核心转换正确的证据较强，但参数更名带来未覆盖的旧关键字兼容性回归。未执行项目/测试/替代实现。

## 公开目标和需求—断言双向表

题面要求 da.ravel 接受 array_like，例子是 [0,0]，并给出先转换再 reshape 的建议；asasanyarray 是拼写错误，base 已有 asanyarray 导入。不是要求实现所有 NumPy order 参数或单独重写 append。公开提示仅改非测试源码与题面建议测试并不使 solver 必须提交测试；实际提示交付仍 unknown。

| 需求/旧行为 | 公开依据 | 断言与 helper | 覆盖评价 |
|---|---|---|---|
| 列表接受/值和 shape 正确 | user_prompt [0,0] | test_ravel_with_array_like: assert_eq(np.ravel([0,0]),da.ravel([0,0])) | 直接覆盖；noop 在更早标量断言中断，不意味着后续列表断言曾运行 |
| 标量、tuple、nested tuple-in-list | 题面一般 array_like；asanyarray文档 | 同一函数对 0、(0,0)、[(0,),(0,)] 各 assert_eq | 合理扩展；共4个值比较，全部零值，未验证新输入路径的元素排列、非零值保真、空输入、多类型 |
| 返回 Dask Array | Dask asanyarray 文档和公开接口惯例 | 每个输入另 assert isinstance(da.ravel(...), da.core.Array)，4个断言 | 类型要求可公开推断，不强制调用特定转换函数；不是纯 NumPy 结果也可接受 |
| 既有 Dask 0D/1D/2D/3D、flatten、图大小 | test_ravel 旧断言 | 两种chunks比较值；2D图长度增加每行chunk个任务；0D/3D/flatten/da.ravel(a) | 已核 P2P，限制 eager materialization 类破坏 |
| 已知与未知长度1D | test_ravel_1D_no_op | 普通及布尔筛选后 ravel 与 NumPy 相等 | 已核 P2P；不能推出未知长度多维reshape无限支持 |
| 旧 array= 关键字调用 | base routines.py:1197函数签名，无 positional-only 标记 | 无新/旧 ravel 测试传关键字 | 缺失；gold改成array_like会拒绝合法旧调用 |

全部8个新增断言及其唯一新函数已读，无新fixture。assert_eq（array/utils.py:202–328）对 Dask 检查 HLG命名/唯一性、元数据维数/类型、compute(scheduler='sync')后shape与dtype自洽，再 allclose；不是仅“无异常”。allclose:176–185 对普通数值经np.allclose，故不是任意 dtype 的严格逐比特验证，尤其对不同adt类型的比较不应夸大为总是强制同dtype。零值样本无法区分新非Dask路径的错误重排或错误填零；现有 Dask P2P含非零随机数据，但不等于列表路径非零覆盖。

## 全部 gold、相关调用者与回归

gold仅两行：ravel(array)→ravel(array_like)，return asanyarray(array_like).reshape((-1,))。asanyarray:4058–4095对现有Array直接返回；对to_dask_array/xarray/list含Array各走已有转换；普通标量/列表用np.asanyarray，再from_array(..., chunks=a.shape, getitem=getter_inline, asarray=False)。其保留ndarray子类作为chunks的语义明确。Array.ravel→routines.ravel，flatten是别名；reshape:146–238保留1D -1快速返回、单分区任务/多分区rechunk路径。__init__.py导出同一函数。没有新增依赖或计算整个旧Dask Array的显式路径。

check26具体静态回归：旧 da.ravel(array=da.from_array(np.arange(4),chunks=2)) 可以按签名绑定 array；gold签名不含 array 也无 **kwargs，Python将报 unexpected keyword argument。derived_from:663–711在通常分支只改docstring后返回原method，不提供参数别名，因此不能消除此回归。未实际执行但这是由完整签名/装饰器核读得到的确定绑定差异；公开示例形参写array_like是实现建议，不足以明确授权移除既有关键字。保留def ravel(array)并在体内转换是合理非gold方案，当前测试并不要求更名，应可满足所读新旧断言，尚未完整执行验证。

asarray取代asanyarray可满足这些普通输入，但子类chunk语义不等价；本题不把gold当唯一正确文本。matrix/第三方后端及to_dask_array返回值的reshape具体行为未全面核证。原直接NumPy输入曾返回NumPy对象，gold返回Dask符合所选公开转换语义；不能同时把这种有题意依据的变化泛称破坏。没有追读 NumPy append 内部；题面只是动机。

## 原运行、输入与交付

唯一 F2P test_ravel_with_array_like：noop日志582–598在第一项标量0失败，AttributeError:'int' object has no attribute 'reshape'，其余新增断言在该次未到达；gold该函数通过且包含全部8断言。P2P468逐ID机械对照均PASSED；语义重点仅test_ravel及test_ravel_1D_no_op，其他测试不作为完整覆盖证明。运行整份test_routines.py，noop 1 failed/560 passed，gold561 passed，无skip/xfail，92 warnings，均完成且安装RC0。具体原件和行号见附录。

公开base=9bb586a6b8fac1983b7cea3ab399719f93dbbb29，baseline/stage指定指针一致；gold原candidate.patch与私有gold逐字节一致，projection仅routines.py。日志git status在grader准备阶段显示noop干净、gold只改该文件；真正 diff段333或338之后分别为空/对应gold，git show是基线提交。测试checkout base再apply成功，诊断恢复/保护项成功；没有据此推断actor初态或绝对不可伪造。runner_integrity_changed=false为该grader局部正证据。

历史dask7138-pytest-v1派生镜像的实际ID和scripts digest见附录；原日志Python3.8.15、pytest7.4.4，安装命令python -m pip install --no-deps -e .，导入/testbed/dask。run_refs无单独recipe/image构建原件，环境record入口引用只是线索，未擅自扩读；因此不声称已核完整镜像构建或所有依赖锁定。原安装未阻断不能替代实际actor。

## 开发需求及唯一下一步

| 操作/资产 | 公开依据 | 已有证据适用范围/缺口 | 最小公开命令建议（未执行） |
|---|---|---|---|
| Python、NumPy、toolz、Dask、pytest，本地源编辑 | setup.py、routines导入、题面 | 历史grader导入/安装成功；actor UID/HOME/cwd/PATH、解释器、工作树初始改动、权限unknown | id；git rev-parse HEAD；git status --porcelain=v1；打印sys.executable/dask.__file__/numpy版本 |
| list/标量及既有惰性数组接口 | 公开例及旧test_ravel | 只需内存小数据，不需外部资产/网络/GPU | python -c运行da.ravel([0,0])及非零嵌套列表，对比np.ravel；核返回Array |
| 窄旧回归/合法交付 | test_ravel两函数；hints非测试约束 | 历史投影仅源码，当前候选未有 | python -m pytest -q dask/array/tests/test_routines.py::test_ravel dask/array/tests/test_routines.py::test_ravel_1D_no_op；git diff --stat |

唯一优先下一步：将既有 array= 关键字保留要求交给题目维护者确认并处理gold参考，附上述由签名直接推得的例子；不必为确定的参数绑定另安排CPU，更不需全仓实验。随后正常actor开发核验由任务二接线，不在本轮执行。

## 实读范围

完整读本题公开prompt/bundle/identity/environment说明、封存public_read，私有test/gold完整、grading expected全列表/validation、授权run_refs/source_refs和environment_record本题字段、五中性方法。源码实际区段：routines.py:1–50,1160–1230；array/core.py:1845–1888,4020–4100；reshape.py:146–238；array/__init__.py:20–38；utils.py:663–711；array/utils.py:176–328。旧测试test_routines.py:1–75,945–990；test_array_core.py:2490–2556（这是公开相关转换回归，非本题执行selector/P2P）；setup.py/setup.cfg/conftest.py。gold/测试patch整段与原candidate逐字节核对。

未读所有468 P2P主体、完整from_array/stack/getter_inline内部、第三方库、全部import链、其余调用者、NumPy append、其它题或旧质量结论。只对授权原日志取命令/状态/相关失败/恢复/初态区段；机械读状态≠语义全覆盖。没有执行、导入、联网、安装、模型/CPU实验或修改项目。

## 原件身份、命令与逐测试附录

以下P=/runs/swegym_quality_expansion_20260925/public/dask__dask-7138/base（实际根为本文工作区）；private=/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/dask__dask-7138。原路径均相对工作区 /Users/roger/Desktop/claude-code-verl-stage0h。

source tag=`xingyaoww/sweb.eval.x86_64.dask_s_dask-7138:latest`；期望manifest digest=`sha256:91df52cb66bb64003ecf4721832eae373c701536aa3dcb85ddc7d9e0ea757736`。

### gold

ledger `runs/env_recipe_repair_20260919/round2b/runs/dask7138-pytest-v1-gold/ledger.jsonl:1`；log `runs/env_recipe_repair_20260919/round2b/runs/dask7138-pytest-v1-gold/eval_logs/evallog_replay-er19-r2-dask7138-_979d801a.eval.log`，SHA256 `1cbe85b89c848aa3872a7e50f88db516e72cd601774f434ed85ac8ee3270997a`（独立hash核对一致）。

- actual image ID：`"sha256:281a1a511f29617325b7663eba79fe6a51d9710c9fbb2ee40f13df09f8332389"`
- derived recipe：`"dask7138-pytest-v1"`
- scripts digest：`"sha256:b3c18dbeea69cce27bd9e1e85a1e7caad3529b53b35a4b14ce46268e34535f1b"`
- raw gold patch SHA：`"sha256:d68ca41cd89d5607d0db853a76b4161314033cc70aeefaa59385e828bcf6644b"`
- projection included：`["dask/array/routines.py"]`
- install：`{"install_rc_last_command": 0, "install_seconds": 2.445, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 0, "test_seconds": 14.861}`
- resource原字段：`{"mem_peak_mb": 1280.887, "mem_peak_unavailable_or_zero": false}`

原policy={"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}；原budgets={"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}。不改资源字段名/单位。

原命令、平台和汇总：

- log:583 `+ pytest -n0 -rA --color=no dask/array/tests/test_routines.py`
- log:585 `platform linux -- Python 3.8.15, pytest-7.4.4, pluggy-1.5.0`
- log:1182 `====================== 561 passed, 92 warnings in 13.78s =======================`

逐F2P与已语义阅读的相关P2P身份（状态来自原日志；其余expected只机械核对）：

| 类别 | ID | 原状态/行 |
|---|---|---|
| F2P | `dask/array/tests/test_routines.py::test_ravel_with_array_like` | PASSED / 1067 |
| P2P | `dask/array/tests/test_routines.py::test_ravel` | PASSED / 1065 |
| P2P | `dask/array/tests/test_routines.py::test_ravel_1D_no_op` | PASSED / 1066 |

expected F2P=1、P2P=468；所有P2P逐ID映射均PASSED，无缺席；这仅是身份与状态核对。原parser={"apply_ok": true, "num_parsed_outside_segment": 0, "num_parsed_tests": 561, "parser_source": "swegym_parsers@242429c1", "reference_missing": [], "reference_skipped": [], "resolution": "RESOLVED_FULL"}；原cleanup={"detail": "", "removed": true, "steps": ["rm:ok"]}。

### noop

ledger `runs/env_recipe_repair_20260919/round2b/runs/dask7138-pytest-v1-noop/ledger.jsonl:1`；log `runs/env_recipe_repair_20260919/round2b/runs/dask7138-pytest-v1-noop/eval_logs/evallog_replay-er19-r2-dask7138-_cc53c2de.eval.log`，SHA256 `8cc3ad60155fcb25c890175031179edb08429ef10f348a2680af75b5f8e7fe7f`（独立hash核对一致）。

- actual image ID：`"sha256:281a1a511f29617325b7663eba79fe6a51d9710c9fbb2ee40f13df09f8332389"`
- derived recipe：`"dask7138-pytest-v1"`
- scripts digest：`"sha256:b3c18dbeea69cce27bd9e1e85a1e7caad3529b53b35a4b14ce46268e34535f1b"`
- raw gold patch SHA：`null`
- projection included：`[]`
- install：`{"install_rc_last_command": 0, "install_seconds": 2.448, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 1, "test_seconds": 16.326}`
- resource原字段：`{"mem_peak_mb": 1460.148, "mem_peak_unavailable_or_zero": false}`

原policy={"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}；原budgets={"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}。不改资源字段名/单位。

原命令、平台和汇总：

- log:563 `+ pytest -n0 -rA --color=no dask/array/tests/test_routines.py`
- log:565 `platform linux -- Python 3.8.15, pytest-7.4.4, pluggy-1.5.0`
- log:1180 `================= 1 failed, 560 passed, 92 warnings in 14.93s ==================`

逐F2P与已语义阅读的相关P2P身份（状态来自原日志；其余expected只机械核对）：

| 类别 | ID | 原状态/行 |
|---|---|---|
| F2P | `dask/array/tests/test_routines.py::test_ravel_with_array_like` | FAILED / 1179 |
| P2P | `dask/array/tests/test_routines.py::test_ravel` | PASSED / 1063 |
| P2P | `dask/array/tests/test_routines.py::test_ravel_1D_no_op` | PASSED / 1064 |

expected F2P=1、P2P=468；所有P2P逐ID映射均PASSED，无缺席；这仅是身份与状态核对。原parser={"apply_ok": true, "num_parsed_outside_segment": 0, "num_parsed_tests": 561, "parser_source": "swegym_parsers@242429c1", "reference_missing": [], "reference_skipped": [], "resolution": "RESOLVED_NO"}；原cleanup={"detail": "", "removed": true, "steps": ["rm:ok"]}。

## 审查边界与检查编号

实际actor消息（user/system/tool及hints是否交付）、实际初始工作树HEAD/status/diff、来源规定初改、忽略资产、UID/HOME/cwd/PATH、源码权限与包来源、资源与网络均unknown。历史grader恢复后的干净base不能替代这些事实。公开包没有导出某资产不证明镜像缺资产。grader的network=deny_all不证明actor网络相同；未发现最小功能需要外部服务。正式镜像构建供应网络与测试期网络分开。

原编号稀疏判断：1有base/patch/投影/原运行局部对应证据；2有源码根因与注明范围的noop；3 unknown（实际输入）；4/6/7/8/9/10/16/17/18/19/20/21按上文grader局部证据，actor部分unknown；23需求充分性与具体规格争议见正文，24非gold误拒、25漏测、26新增回归、27gold局部正确性/完整性分别论证；28不将自加样例强行写成来源要求。29 actual actor答案暴露unknown，不能因审查者已知gold改成actor泄漏；30未查实际网络取答案；31只核恢复/保护局部记录，非完整攻击审计；33/34/35/36真实模型和训练资格unknown；37仅注明原环境配方差异；38未重跑干净复验；39未跨题验证；40封存合规不能证明无漏检/误拒/抽样偏差。未列编号视为not_checked。

usage：本主审获授权看本题隐藏test.patch、gold.patch、expected、历史原noop/gold日志及本题public_read。未读history/旧质量记录、reviewer、根汇总、其他包；不能把本审查材料交给独立solver。additional_exclusions=[]；revision_refs=[]；无新CPU/模型或工具计费观测，costs相应为null。全文是诊断审查，非训练/正式评测批准。封存后不再改写，等待明确history release。
