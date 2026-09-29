# dask__dask-9378 独立初判（封存前）

2026-09-25；fresh reviewer；static_review / needs_review。公开目标清楚、历史 gold 分差成立，但存在直接涉及核心要求的测试盲点：ones_like/zeros_like 的比较 helper 并不逐元素验证 mask 相等。建议保留为评分敏感的开发诊断候选，优先核实这个盲点；不能按现有 reward 认定 mask 保留已被完整验收，更非训练/正式评测资格。

## 1. 身份、公开输入与初态

base=`8b95f983c232c1bd628e9cba0695d3ef229d290b`，465个跟踪条目的静态导出；public/base_identity记录 blob/path/mode已核，reviewer未重做全导出哈希。public/grading/gold源码对应，run_refs精确原gold candidate.patch与本包gold字节完全一致且哈希正确。题面报2022.7.1，任务基线2022.8，历史实际包2022.8.0+12.g8b95f983c.dirty，三者不混用。

题面先说明da.ones_like会丢mask，随后明确建议提供 `dask.array.ma.ones_like/zeros_like/empty_like`，沿既有map_blocks包装模式；因此测试要求da.ma入口有公开依据。修da.ones_like并同时提供da.ma同义入口是合理非gold路线；只修da.ones_like、不实现题面明确提出的ma版本，不能简单认定其被测拒绝就是误杀。

public_hints计划要求非测试源文件、允许窄测试；actual actor实际完整消息、hints/system/tool交付、HEAD/status/diff、准备阶段初态、来源规定改动、忽略资产、权限均unknown。历史git show是基线提交，日志含该提交对其它测试的修改不等于工作树污染或本题初始未提交diff。

## 2. 根因/实现和调用者

`dask/array/ma.py` 基线无三个函数；现有 filled/fix_invalid/getdata/getmaskarray等(:21–24,100–115)用asanyarray+map_blocks。gold增加三个同模式函数，传给np.ma.core对应函数，保留Dask分块惰性路径。`core.py:4589–4612` asanyarray对Dask Array原样返回，普通array-like用from_array，不像强制np.asarray那样直接抹掉mask。`core.py:523–535,795–814,850–879` map_blocks推断meta/dtype、调用blockwise；`array/blockwise.py:229–284`构造块函数图。

原da.ones_like/zeros_like/empty_like位于creation.py:31–181，按shape/dtype/chunks创建数组，gold没有修改这些入口；这与新ma函数的公开提议一致，不是已证漏修。相关既有 masked_array(:118–151)有shape检查、dtype特殊透传；可以用来识别kwargs并非总能直接安全透传。

## 3. 需求—断言双向表（新增函数全部参数化项）

| 需求 | 公开依据 | F2P/决定性断言 | 覆盖与问题 |
| --- | --- | --- | --- |
| da.ma.ones_like返回1且保留mask | 原题三函数及建议命名 | test_like_funcs[ones_like]，mask=[[T,F],[T,T],[F,T]]、data=arange(6).reshape(3,2)，masked_array chunks=2；assert_eq(res,np.ma.core.ones_like(a)) | 值/shape/dtype/type/meta/chunk一致有检查；mask相等没有独立断言 |
| da.ma.zeros_like返回0且保留mask | 同上 | test_like_funcs[zeros_like]，同fixture、assert_eq(res,sol) | 同样缺少直接mask相等 |
| da.ma.empty_like保留mask | 同上，empty值本就不确定 | test_like_funcs[empty_like]，assert_eq(da.ma.getmaskarray(res),np.ma.getmaskarray(sol)) | 对布尔mask直接比较，核心要求覆盖；不测res数据dtype/类型本身 |
| 惰性Dask array和多个chunk上正确 | 库既有模式、题面提到map_blocks | 前两支 assert_eq->_get_dt_meta_computed->_check_chunks | 检查块shape/dtype和结果；没有断言构图阶段不急算或固定chunk保持 |
| 输入无mask/全mask/空/标量/不同dtype | NumPy式array-like及相关旧API | 此次仅单个3x2整数/混合mask fixture | 部分/缺失，不能泛化所有输入 |
| dtype/order等kwargs约定 | 相关creation.py与派生NumPy接口；题面未明确逐参数 | 本次未传kwargs | 非核心边界待界定；不应私自扩充验收要求 |

反向看新增test patch全部19行已读：参数化3值、fixture、getattr入口、res/sol调用及两类断言；没有检查源码写法，empty_like不比较未初始化数据是合理的。逐F2P历史身份与状态见附录。

## 4. helper盲点、非gold路线与gold边界

关键盲点（25）：`dask/array/utils.py:172–179` 的 allclose 在任何参数有mask时执行 `np.ma.allclose(a,b,masked_equal=True)`；`assert_eq:324–374`核shape/type/meta后直接调它，没有mask逐元素equal。_check_chunks(:225–240)只核shape/dtype，_get_dt_meta_computed(:243–279)也没mask相等。因此“同dtype同shape的MaskedArray、值为全1/全0、mask错误地全False或过度屏蔽”在ones/zeros支可能通过；这些候选违反题目核心mask保留目标。这里是明确的源码覆盖缺口及静态预计的漏放路线，未运行这些候选，不声称已实测拿分。empty支明确取mask则能拒绝对应错误。相关P2P不会调用新函数，所以不能补这个缺口。

gold本身对默认参数按块调用NumPy masked函数，与公开需求及测试fixture静态一致；盲点是验收不足，不等于gold默认mask错误。合法非gold可在保留输入mask下生成块数据、重建masked_array，或共享通用wrapper；只要结果的mask/值/meta与合理语义一致，不必调用np.ma.core或复制gold结构。

kwargs边界：gold `**kwargs`直接给map_blocks，dtype被core.py:528绑定为输出元数据，不传入numpy函数；blockwise同样把dtype作为独立参数而非kwargs2(:229–254)。若请求dtype改变，静态预计可能出现metadata dtype与实际块dtype不同。chunks/shape参数也不能简单按整个数组的NumPy语义转发到每块。然而`utils.py:564–573,797–807`的get_named_args忽略**kwargs，derived_from会给NumPy额外参数标“不支持”；因此不能仅凭有**kwargs就要求gold完整实现全部NumPy参数，也不能直接把dtype现象记成题意错误或旧行为回归。它是值得检查文档实际呈现/拒绝行为的边界，优先级低于核心mask漏验。

其它缺口：empty_like只看mask，返回原输入或zeros_like也可能符合该断言；empty不要求随机垃圾值，不能为了强区分而加入无效“必须不同值”要求。合理检查是dtype/shape/type/惰性等契约而非随机内容。未运行全仓回归；gold只增加函数，不据未知认定它破坏旧行为。

## 5. 相关P2P、历史命令与条件

完整读test_masked.py基线429行及新增补丁：functions列表27种运算分别应用于basic/mixed_concatenate/mixed_random；random mask组合既有随机性不可由一次通过证明稳定。已核全部reduction/allmasked参数化、assert_eq_ma helper(:228–238)会显式比mask、arg/cumulative、accessors、masked_array dtype/shape/fill值异常、set_fill_value、average keepdims、arithmetic、count。总134P2P逐ID对拍历史PASSED；这批旧测试涵盖旧masked生态，并不访问新增3函数，因此不能挽救其mask漏检。当前全仓/多次重复未验。

只引用run_refs所指 `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-1/ledger.jsonl` 第11行noop、第12行gold（未读其他行内容）；原日志为 cbe4c60c/36998202。原命令 `pytest -n0 -rA --color=no dask/array/tests/test_masked.py`，此前 `python -m pip install --no-deps -e .`，source conda/activate testbed/cd /testbed。noop日志:912–919为Python3.10.14/pytest8.3.2，137 collected；:1071–1104三个参数分别在patched test :439的getattr因缺少ma入口而失败，尚未进入mask比较；:1255为3 failed/134 passed。gold :943–950同命令137 collected，:1240为137 passed。分差说明缺失API被补齐并通过这些断言，不能证明mask性质完整。

账本F2P0/3→3/3、134P2P均pass、num_parsed137、无段外解析/缺失/skip；install rc0、test rc1/0、导入/testbed/dask/__init__.py，gold投影仅dask/array/ma.py，无ignored/unsupported，cleanup removed/rm:ok。source镜像tag为xingyaoww/sweb.eval.x86_64.dask_s_dask-9378:latest，expected digest=`sha256:d59dc8d2aa23abc26c301754af4623f7bbad5d798713a6c5caa2d2113b6691b1`；actual image ID=null，不能把expected当实际ID。历史rh2grader UID54322，network deny_all，cpus2.0、memory_bytes4294967296、pids512、deadline3600s；mem_peak_mb原字段noop287.969/gold261.359，不臆测单位实现。runner digest一致；无独立本题recipe after文件定位、未读历史评分器源代码归档内容，只按日志实际命令/投影/解析记录解释。

日志noop:210–214显示历史grader在打可信test前工作树clean；gold相应状态显示ma.py变更。未采集actual actor准备后git status --porcelain/v1退出码、初态差分、ignored资产，所以这些仍unknown。

## 6. 开发需求与最小事实请求

| 操作/资产 | 公开依据 | 已有证据适用谁/何条件 | 缺口 | 最小公开命令/预期 |
| --- | --- | --- | --- | --- |
| NumPy、dask.array.ma、本工作区代码导入 | 原题imports；setup.py array numpy>=1.18 | 历史grader可editable安装/import | actor解释器、NumPy版本、源码路径、UID/HOME/cwd/PATH unknown | 实际CC shell打印这些及HEAD/status/diff，保存逐命令rc |
| 公开masked-array流程 | 原题三元素示例及ma版本请求 | 历史隐藏测试可区分API缺失 | actual actor用户流程未验 | 构造原题array，调用ma三函数并compute；修后ones/zeros分别为[1,1,--]/[0,0,--]，empty只核mask及结构 |
| 相关窄测试/安装 | develop.rst:99–113、既有test_masked | 历史同文件137项执行 | actorpytest/plugin、依赖写权限unknown | `python -m pytest -q dask/array/tests/test_masked.py`；base旧测试结果不等于新功能已验 |
| 内存数据、局部CPU调度 | 题面内嵌数据与map_blocks | 无外部服务/下载数据必需迹象 | actor资源/临时目录权限unknown | 运行原用户流程，无需GPU/外部权重；未导出资产不意味着缺件 |

唯一优先评分事实：私有受控对照一个仅破坏ones/zeros mask而保持值/type/dtype/shape的候选，用“现有断言”与“直接getmaskarray逐元素相等”分别判断，确认漏检；不能把候选或私有断言送给solver，也不修改生产评分。actor公开原例验证是独立必要缺口，任务二获取；本角色不运行或派发。

## 7. 评分/提交可信范围

本题历史candidate与gold字节/哈希相同，投影包含普通源码ma.py，日志测试实际收集执行，支持这一历史输入输出链。恢复测试的具体可信脚本内容未作为独立文件获得，日志与reference状态不是对任意控制面攻击的证明。actual actor可读可改可提交范围、网络答案获取、真实CC交付仍unknown。不能把historical grader环境当actor开发可用；也不因mask盲点就断言全部任务无效。

## 8. 用途、编号与实际阅读

usage.intended_use=development_diagnostic。reviewer获授权见gold/test/grading/validation/run_refs/source_refs/environment_record、原gold候选和noop/gold原日志，属于私有审查暴露；actual actor是否见未来答案（29）unknown。public题面中的map_blocks建议是公开内容。审查材料不得进入独立solver；不宣称操作系统级隔离。

建议编号：1 pass静态对应且保留actual image ID未知；2 pass缺失API源码/历史getattr失败；3/4/7/8/10/13/14/15/29 unknown；6/9/16/18/19/20/21 pass仅历史命令/角色；17unknown独立脚本恢复边界未全核；23 pass明确ma功能目标；24 pass未强制实现；25 issue核心ones/zeros mask盲点；26unknown无新回归实证；27 pass仅默认参数目标静态合理/窄历史，kwargs完整性unknown；28 pass未自创随机内容要求；31/33/35/36unknown；37not_applicable本题未引用配方修订；38/39not_checked；40unknown。流程合规不证明无漏检/误杀/抽样偏差，其它未列not_checked。

实际阅读：公开prompt/bundle/identity/环境brief，README/CONTRIBUTING全文，setup/develop/配置相关段；ma.py全文件、test_masked.py全文件及补丁所有断言；array/utils.py:172–184,225–386决定性完整比较链，map_blocks核心参数/推断/调用、asanyarray尾部、blockwise参数/kwargs图构造/返回、creation.py前三个like函数、utils.py derived_from/get_named_args。私有run_refs及原ledger限定本题行，日志初态/安装/pytest/失败/结果和每个expected状态、candidate哈希。未读NumPy安装库源码、actual actor实态、归档内评分器代码、全仓其它测试，未读任何public_read/主审/他人review/历史质量结论/根汇总；未执行项目/导入/测试/联网/容器/模型/子agent。静态反例是源码推断，未包装成运行已证。封存后不改，等明确cross_review release。

## 附录：逐 expected ID 原日志对拍（历史，不是本轮重跑）
- noop ledger：`runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-1/ledger.jsonl:11`；选中行SHA匹配=True。log：`runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-1/eval_logs/evallog_replay-f216-baseline01-w_cbe4c60c.eval.log`；全log SHA匹配=True。
- gold ledger：`runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-1/ledger.jsonl:12`；选中行SHA匹配=True。log：`runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-1/eval_logs/evallog_replay-f216-baseline01-w_36998202.eval.log`；全log SHA匹配=True。

| 集合 | expected ID | noop日志状态@行 | gold日志状态@行 |
| --- | --- | --- | --- |
| F2P | `dask/array/tests/test_masked.py::test_like_funcs[empty_like]` | FAILED @1254 | PASSED @1239 |
| F2P | `dask/array/tests/test_masked.py::test_like_funcs[zeros_like]` | FAILED @1253 | PASSED @1238 |
| F2P | `dask/array/tests/test_masked.py::test_like_funcs[ones_like]` | FAILED @1252 | PASSED @1237 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>4]` | PASSED @1153 | PASSED @1138 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>1]` | PASSED @1122 | PASSED @1107 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>12]` | PASSED @1188 | PASSED @1173 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>0]` | PASSED @1121 | PASSED @1106 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>7]` | PASSED @1128 | PASSED @1113 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>11]` | PASSED @1160 | PASSED @1145 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>20]` | PASSED @1169 | PASSED @1154 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>6]` | PASSED @1182 | PASSED @1167 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>14]` | PASSED @1163 | PASSED @1148 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>25]` | PASSED @1201 | PASSED @1186 |
| P2P | `dask/array/tests/test_masked.py::test_reductions_allmasked[prod-f8]` | PASSED @1227 | PASSED @1212 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>2]` | PASSED @1151 | PASSED @1136 |
| P2P | `dask/array/tests/test_masked.py::test_reductions_allmasked[sum-i8]` | PASSED @1224 | PASSED @1209 |
| P2P | `dask/array/tests/test_masked.py::test_creation_functions` | PASSED @1204 | PASSED @1189 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>17]` | PASSED @1166 | PASSED @1151 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>6]` | PASSED @1127 | PASSED @1112 |
| P2P | `dask/array/tests/test_masked.py::test_arg_reductions[argmax]` | PASSED @1243 | PASSED @1228 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>18]` | PASSED @1167 | PASSED @1152 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>18]` | PASSED @1194 | PASSED @1179 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>7]` | PASSED @1156 | PASSED @1141 |
| P2P | `dask/array/tests/test_masked.py::test_reductions_allmasked[prod-i8]` | PASSED @1226 | PASSED @1211 |
| P2P | `dask/array/tests/test_masked.py::test_reductions[mean-i8]` | PASSED @1210 | PASSED @1195 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>16]` | PASSED @1192 | PASSED @1177 |
| P2P | `dask/array/tests/test_masked.py::test_reductions[any-i8]` | PASSED @1220 | PASSED @1205 |
| P2P | `dask/array/tests/test_masked.py::test_tokenize_masked_array` | PASSED @1118 | PASSED @1103 |
| P2P | `dask/array/tests/test_masked.py::test_set_fill_value` | PASSED @1247 | PASSED @1232 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>14]` | PASSED @1135 | PASSED @1120 |
| P2P | `dask/array/tests/test_masked.py::test_filled` | PASSED @1205 | PASSED @1190 |
| P2P | `dask/array/tests/test_masked.py::test_reductions_allmasked[any-f8]` | PASSED @1239 | PASSED @1224 |
| P2P | `dask/array/tests/test_masked.py::test_reductions[max-i8]` | PASSED @1218 | PASSED @1203 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>18]` | PASSED @1139 | PASSED @1124 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>14]` | PASSED @1190 | PASSED @1175 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>5]` | PASSED @1154 | PASSED @1139 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>21]` | PASSED @1197 | PASSED @1182 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>19]` | PASSED @1168 | PASSED @1153 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>22]` | PASSED @1198 | PASSED @1183 |
| P2P | `dask/array/tests/test_masked.py::test_reductions_allmasked[any-i8]` | PASSED @1238 | PASSED @1223 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>1]` | PASSED @1177 | PASSED @1162 |
| P2P | `dask/array/tests/test_masked.py::test_cumulative` | PASSED @1244 | PASSED @1229 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>23]` | PASSED @1172 | PASSED @1157 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>16]` | PASSED @1137 | PASSED @1122 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>21]` | PASSED @1170 | PASSED @1155 |
| P2P | `dask/array/tests/test_masked.py::test_reductions[any-f8]` | PASSED @1221 | PASSED @1206 |
| P2P | `dask/array/tests/test_masked.py::test_arithmetic_results_in_masked` | PASSED @1250 | PASSED @1235 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>10]` | PASSED @1186 | PASSED @1171 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>20]` | PASSED @1196 | PASSED @1181 |
| P2P | `dask/array/tests/test_masked.py::test_reductions_allmasked[max-f8]` | PASSED @1237 | PASSED @1222 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>21]` | PASSED @1142 | PASSED @1127 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>23]` | PASSED @1144 | PASSED @1129 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>25]` | PASSED @1146 | PASSED @1131 |
| P2P | `dask/array/tests/test_masked.py::test_reductions[std-f8]` | PASSED @1215 | PASSED @1200 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>1]` | PASSED @1150 | PASSED @1135 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>10]` | PASSED @1159 | PASSED @1144 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>24]` | PASSED @1173 | PASSED @1158 |
| P2P | `dask/array/tests/test_masked.py::test_arg_reductions[argmin]` | PASSED @1242 | PASSED @1227 |
| P2P | `dask/array/tests/test_masked.py::test_reductions_allmasked[mean-f8]` | PASSED @1229 | PASSED @1214 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>11]` | PASSED @1132 | PASSED @1117 |
| P2P | `dask/array/tests/test_masked.py::test_reductions[sum-f8]` | PASSED @1207 | PASSED @1192 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>11]` | PASSED @1187 | PASSED @1172 |
| P2P | `dask/array/tests/test_masked.py::test_reductions_allmasked[std-i8]` | PASSED @1232 | PASSED @1217 |
| P2P | `dask/array/tests/test_masked.py::test_reductions_allmasked[min-f8]` | PASSED @1235 | PASSED @1220 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>0]` | PASSED @1176 | PASSED @1161 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>2]` | PASSED @1178 | PASSED @1163 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>19]` | PASSED @1195 | PASSED @1180 |
| P2P | `dask/array/tests/test_masked.py::test_reductions[all-i8]` | PASSED @1222 | PASSED @1207 |
| P2P | `dask/array/tests/test_masked.py::test_reductions_allmasked[all-i8]` | PASSED @1240 | PASSED @1225 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>3]` | PASSED @1124 | PASSED @1109 |
| P2P | `dask/array/tests/test_masked.py::test_reductions[prod-i8]` | PASSED @1208 | PASSED @1193 |
| P2P | `dask/array/tests/test_masked.py::test_reductions_allmasked[var-f8]` | PASSED @1231 | PASSED @1216 |
| P2P | `dask/array/tests/test_masked.py::test_reductions_allmasked[sum-f8]` | PASSED @1225 | PASSED @1210 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>26]` | PASSED @1175 | PASSED @1160 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>3]` | PASSED @1152 | PASSED @1137 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>17]` | PASSED @1193 | PASSED @1178 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>8]` | PASSED @1129 | PASSED @1114 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>13]` | PASSED @1189 | PASSED @1174 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>8]` | PASSED @1184 | PASSED @1169 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>3]` | PASSED @1179 | PASSED @1164 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_output_type` | PASSED @1203 | PASSED @1188 |
| P2P | `dask/array/tests/test_masked.py::test_from_array_masked_array` | PASSED @1119 | PASSED @1104 |
| P2P | `dask/array/tests/test_masked.py::test_masked_array` | PASSED @1246 | PASSED @1231 |
| P2P | `dask/array/tests/test_masked.py::test_count` | PASSED @1251 | PASSED @1236 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>26]` | PASSED @1202 | PASSED @1187 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>19]` | PASSED @1140 | PASSED @1125 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>4]` | PASSED @1125 | PASSED @1110 |
| P2P | `dask/array/tests/test_masked.py::test_average_weights_with_masked_array[False]` | PASSED @1248 | PASSED @1233 |
| P2P | `dask/array/tests/test_masked.py::test_reductions[all-f8]` | PASSED @1223 | PASSED @1208 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>24]` | PASSED @1200 | PASSED @1185 |
| P2P | `dask/array/tests/test_masked.py::test_accessors` | PASSED @1245 | PASSED @1230 |
| P2P | `dask/array/tests/test_masked.py::test_average_weights_with_masked_array[True]` | PASSED @1249 | PASSED @1234 |
| P2P | `dask/array/tests/test_masked.py::test_reductions[var-f8]` | PASSED @1213 | PASSED @1198 |
| P2P | `dask/array/tests/test_masked.py::test_reductions[mean-f8]` | PASSED @1211 | PASSED @1196 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>0]` | PASSED @1149 | PASSED @1134 |
| P2P | `dask/array/tests/test_masked.py::test_reductions_allmasked[min-i8]` | PASSED @1234 | PASSED @1219 |
| P2P | `dask/array/tests/test_masked.py::test_tensordot` | PASSED @1148 | PASSED @1133 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>5]` | PASSED @1181 | PASSED @1166 |
| P2P | `dask/array/tests/test_masked.py::test_reductions[max-f8]` | PASSED @1219 | PASSED @1204 |
| P2P | `dask/array/tests/test_masked.py::test_reductions_allmasked[std-f8]` | PASSED @1233 | PASSED @1218 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>12]` | PASSED @1133 | PASSED @1118 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>7]` | PASSED @1183 | PASSED @1168 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>22]` | PASSED @1171 | PASSED @1156 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>5]` | PASSED @1126 | PASSED @1111 |
| P2P | `dask/array/tests/test_masked.py::test_reductions[var-i8]` | PASSED @1212 | PASSED @1197 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>24]` | PASSED @1145 | PASSED @1130 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>15]` | PASSED @1191 | PASSED @1176 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>12]` | PASSED @1161 | PASSED @1146 |
| P2P | `dask/array/tests/test_masked.py::test_reductions_allmasked[mean-i8]` | PASSED @1228 | PASSED @1213 |
| P2P | `dask/array/tests/test_masked.py::test_reductions_allmasked[all-f8]` | PASSED @1241 | PASSED @1226 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>9]` | PASSED @1158 | PASSED @1143 |
| P2P | `dask/array/tests/test_masked.py::test_reductions[prod-f8]` | PASSED @1209 | PASSED @1194 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>9]` | PASSED @1130 | PASSED @1115 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>17]` | PASSED @1138 | PASSED @1123 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>13]` | PASSED @1162 | PASSED @1147 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>8]` | PASSED @1157 | PASSED @1142 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>9]` | PASSED @1185 | PASSED @1170 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>10]` | PASSED @1131 | PASSED @1116 |
| P2P | `dask/array/tests/test_masked.py::test_copy_deepcopy` | PASSED @1120 | PASSED @1105 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>2]` | PASSED @1123 | PASSED @1108 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>15]` | PASSED @1164 | PASSED @1149 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>25]` | PASSED @1174 | PASSED @1159 |
| P2P | `dask/array/tests/test_masked.py::test_reductions[min-i8]` | PASSED @1216 | PASSED @1201 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>15]` | PASSED @1136 | PASSED @1121 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>20]` | PASSED @1141 | PASSED @1126 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>13]` | PASSED @1134 | PASSED @1119 |
| P2P | `dask/array/tests/test_masked.py::test_reductions[sum-i8]` | PASSED @1206 | PASSED @1191 |
| P2P | `dask/array/tests/test_masked.py::test_reductions_allmasked[var-i8]` | PASSED @1230 | PASSED @1215 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>23]` | PASSED @1199 | PASSED @1184 |
| P2P | `dask/array/tests/test_masked.py::test_reductions_allmasked[max-i8]` | PASSED @1236 | PASSED @1221 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>22]` | PASSED @1143 | PASSED @1128 |
| P2P | `dask/array/tests/test_masked.py::test_reductions[min-f8]` | PASSED @1217 | PASSED @1202 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_random[<lambda>4]` | PASSED @1180 | PASSED @1165 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>6]` | PASSED @1155 | PASSED @1140 |
| P2P | `dask/array/tests/test_masked.py::test_basic[<lambda>26]` | PASSED @1147 | PASSED @1132 |
| P2P | `dask/array/tests/test_masked.py::test_mixed_concatenate[<lambda>16]` | PASSED @1165 | PASSED @1150 |
| P2P | `dask/array/tests/test_masked.py::test_reductions[std-i8]` | PASSED @1214 | PASSED @1199 |
