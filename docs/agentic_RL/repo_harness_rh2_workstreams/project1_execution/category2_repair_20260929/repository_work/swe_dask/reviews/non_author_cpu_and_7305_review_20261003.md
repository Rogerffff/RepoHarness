# Dask 四题 CPU 原件与 7305 v3 非作者窄核

2026-10-03。**7656、9378、7138 的实际 CPU 证据与冻结矩阵相符；7305 v3 的公开依据、auto 正对照及实际 13 份全模块＋4 份 F2P 定向证据核查通过。范围内无未关闭阻断。四题正式修订 consumer、可信非 root 评分仍待交付，本报告不授予正式 reward、GPU 探针或训练资格。**

核查者是非作者 Codex subagent，没有参与作者修改或 CPU 运行；已接触私有 gold、候选和作者报告，属于已知结果的证据核查，**不是 fresh 公开盲审**。本轮只读本地原件和 archive，做 SHA、日志、源码及 AST 静态核对；没有导入 Dask、运行 pytest、CPU／容器／SSH 实验。仅写本报告与[同名 JSON](non_author_cpu_and_7305_review_20261003.json)。公开题面未改变。

## 逐题结论与边界

| 题目 | 原件支持的结果 | 保留边界与剩余事项 |
| --- | --- | --- |
| 7656 | gold 接受；noop／wrong_result_type／opaque 拒绝。每份49参考完整，48原P2P全过 | 公开 default_nested 在首对象建图即失败，后续 nested 分支未执行；正式 setup900 与非 root 评分待做 |
| 9378 | 用户B规格接受 gold 与 toplevel_only；noop和三个错解拒绝。每份137参考完整，134 P2P全过 | empty只核mask，未增加未初始化值或惰性oracle；正式评分待做 |
| 7138 | compatible_ravel 接受；noop、原gold拒绝。每份470参考完整，原468 P2P全过 | gold只失败新增keyword P2P；正式consumer须追加登记这项P2P |
| 7305 | 新gold_full_auto通过105参考；其余候选拒绝，四项聚焦控制确实触发 | first_last有两个已知旧P2P失败；四定向项各104 P2P未执行；完整正式17行矩阵待做 |

7656／9378／7138复用请求指定的[既有非作者静态审查](non_author_7656_9378_7138_material_review_20261003.md)，SHA为 `ebb9570116c26762a61f307e855b373ba078acee8b1afeb46497544454e35dae`。三题revision／有效patch／有效Python／矩阵的字节均未改变。本轮补实际结果与运输边界，没有重审全部历史语义。

## 运输、身份与执行证据

[三题请求](cpu_result_review_request_7656_9378_7138_20261003.json)的31个SHA绑定项全部吻合。9份镜像／诊断清单共447个成员，其文件集合、大小及SHA全部匹配，无额外或缺席文件。五份输入snapshot的tar成员与archive SHA也核实。7656后续说明文件变化、7305的13→17行追加与旧archive分开保留，不把现行摘要当成历史运行输入。

| 诊断attempt | 清单文件数／字节 | 清单SHA256 |
| --- | --- | --- |
| dask7656-cpu-c-20261003-v2 | 67／304405 | `6edf9659a0513db47312edcb727544b5d2aadbdf4fb22713f9755511be61d53a` |
| dask9378-cpu-c-20261003-v1 | 79／555773 | `51295b1ba6b84a338dee520857300100d31fc42daf46731782b3a2d4856b30d7` |
| dask7138-cpu-c-20261003-v1 | 60／548676 | `470df7c38135f0f1a1b7034cd18efa8b005048863e4707841b45394d0dd34b7f` |
| dask7305-cpu-c-20261003-v1 | 77／344778 | `c853586dd94d85e6f0dd0fd266e133748bdd1a0cf647c239326fda07a4736bfd` |
| dask7305-remaining-cpu-c-20261003-v1 | 89／277502 | `9a464cc0eab7afad4cf709b6168215d39c18aef577e57785081c5ed88114f461` |

四个真实CC actor均为2.1.205配脚本桩，无基座模型推理。直接读首请求：原public_hints＋原problem_statement逐字一致；另一个user文本块仅是CC日期提醒。没有新私有测试、候选或gold的题面追加。trajectory实际Bash调用和tool_result分别为5／4／4／3个，命令ID、退出码及capture大小吻合；harness rc0，有completed结果事件，完整日志字节数相符。

四actor实际UID54321，初态HEAD干净，源码从 `/testbed/dask` 导入。prelaunch／activation均ok；真实cgroup为2 CPU、4 GiB、swap0、pids512，bind mount为空，activation写权限DENIED。泛用 `interpreter_in_tool_result`、`bashenv_denied_for_agent` 仍为false，不能报成通过：命令没有打印该检查器所需固定标记，实际解释器及权限由identity／prelaunch／activation原件确认。

30份私有对照实际为**root**独立容器，串行应用生产候选再应用测试；不是可信非root正式评分。每份原日志恰有一对Start/End；只在标记内独立逐参考解析，与status.json完全一致。准备rc全为0、参考无缺席，test rc为0或预期断言失败的1，未见超时、安装或收集异常。SHA、字节及summary退出相符；各候选rm/query rc0、残留为空；四actor容器／网络／桩也无残留。7138及7305追加作业q01的rc75为资源忙、未执行，q02才是完成证据。

冻结source：7656为 `cat2-cpu-r2e064065-swe5-20261003-v1`，manifest `282021962a92b510f077385660ac56acedcd7fac1d97e63db3baa98e4dcc057f`，verify receipt核794成员；其余实际作业为 `cat2-cpu-r2e078079-swe7-git-20261003-v1`，manifest `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`，核837成员。运行解释器均为runtime_cpu_v2。这里核的是固定身份和校验回执，未重新远端校验整个发布或重审共享实现。旧source完成的有效证据无需因后来共用Git修复重跑；两版只含原材料，不能冒称本轮新测试已正式登记。

## 三题结果的准确解释

### 7656：类型、默认字段与嵌套求值

base HEAD `07d5ad0ab1bc8903554b37453f02cc8024460f2a`；Python3.9.19／pandas1.3.5／pytest8.3.2。actual compat_environment确认正式激活读取conda hook，stdlib distutils实际生效。actor ID `sha256:118f47f67994e4d4df700f427404c7620cd2c9eedf3b818f0e8b21d3276babe3`；copy-only grader ID `sha256:50bca237706aed5413899f7fec2123e9933de56293e8ed8169938c86a9e0559b`；基础层与历史pandas wheel SHA保留。

公开原例rc1确为缺 `primary_key`；default_nested同样在第一对象建图失败，尚未执行函数内类型／默认值检查和后续nested对象。公开回归3 passed／49 deselected。

| 私有候选 | 全模块结果 | 实际区分点 |
| --- | --- | --- |
| noop | 1 failed／49 passed／2 xfailed | 建图缺未初始化字段b，未进入类型断言 |
| gold | 50 passed／2 xfailed | 类型、默认值、嵌套求值通过 |
| wrong_result_type | 1 failed／49 passed／2 xfailed | 函数内isinstance失败，实际输入namespace(a=3) |
| opaque | 1 failed／49 passed／2 xfailed | 原类检查通过，字段仍为Delayed；字段值比较触发Truth of Delayed TypeError |

每份49项参考完整、48 P2P全过；全模块含名单外测试，不能混用分母。私有诊断使用安装pandas的actor镜像，不能替代copy-only grader的setup900条件。pip check的distributed／fastparquet／xarray／chest历史冲突仍在，验证只覆盖实际运行路径。

### 9378：B规格两条合理入口

原digest镜像ID `sha256:1e5a0ee850161b35d33d26445f73e872488a45e0e436195af239190b68574096`，HEAD `8b95f983c232c1bd628e9cba0695d3ef229d290b`；Python3.10.14／NumPy1.26.4／SciPy1.14.1／pytest8.3.2，无依赖修改。初版source镜像准备和第五版实际执行分开冻结，没有在途热换。

公开例rc1的准确差异为Dask `[1 1 1]` 对NumPy `[1 1 --]`，最后mask丢失。公开masked模块134 passed，creation选择320 passed／394 deselected。

| 私有候选 | 全模块结果 | 实际区分点 |
| --- | --- | --- |
| noop | 3 failed／134 passed | 三个like函数均在mask比较失败 |
| gold | 137 passed | ma入口通过；不外推顶层也修复 |
| toplevel_only | 137 passed | 缺ma入口时正确顶层路线被B规格接受 |
| ma_mask_none／ma_mask_invert | 各2 failed／135 passed | ones/zeros新增mask比较失败，empty通过 |
| wrong_values_seven | 2 failed／135 passed | mask通过，ones/zeros未屏蔽值7与1/0比较失败 |

六份各137参考完整，134 P2P全过。empty只核mask，不读取未初始化数值，本轮不增加惰性等未批准要求。

### 7138：旧关键字与新pytest配方

HEAD `9bb586a6b8fac1983b7cea3ab399719f93dbbb29`；Python3.8.15／NumPy1.17.5／pytest7.4.4。actor ID `sha256:fdd298b61309ae2df4cb9f528351526b7b3817c42fc34f47f98152a92a520881`，grader ID `sha256:625b404c6c1c40da31df4edfea6052a10fbd30b7fb49d58072b6ee2b215fab13`。新builder保留原基础层，grader只copy wheel、actor安装wheel；不是历史Dockerfile逐层复刻。历史wheel无SHA，不能声称字节相同；当前pytest wheel SHA `b090cdf5ed60bf4c45261be03239c2c1c22df034fbffe691abe93cd80cea01d8`。distributed／zarr／chest的pip check历史冲突仍在。

公开list例rc1确为缺reshape；原 `array=` 调用rc0；公开routines模块560 passed／92 warnings。

| 私有候选 | 全模块结果 | 实际区分点 |
| --- | --- | --- |
| noop | 1 failed／561 passed | F2P先在标量0缺reshape；新增keyword P2P通过 |
| compatible_ravel | 562 passed | 原/新增输入的值、类型和关键字通过 |
| gold | 1 failed／561 passed | F2P通过；只失败新增test_ravel_keyword_array，报unexpected keyword argument array |

每份470参考完整，原468 P2P全过。gold只失败新增P2P，是预先声明的负对照，不是原P2P回归或环境误拒。正式consumer仍须追加登记新P2P，不能只替换test.patch。

## 7305：auto依据、正对照与覆盖

公开原题要求大整数minimum/maximum精确，还明确说明乱序输入末尾最小值的set_index行归属问题。公开base `core.py:3861` 的API接受 `npartitions='auto'`（按内存决定分区），`shuffle.py:503`附近在分位摘要后另做float64插值。新增1000乱序uint64、4输入分区、最小值末尾的实例针对同一行为要求，有公开依据；auto只传给set_index，不传给partition_quantiles。

有效patch在导出base上纯内存逐字应用，与effective_test.py及登记SHA一致。相对原测试仅改变test_set_index_interpolate、增加行为helper；v2七个调用完整保留，auto为第8调用。端点、行多重集合与每分区区间用Python整数比较，不锁定近似内部分界或gold算法；旧小整数过严set比较已经放宽，float控制保留。

gold_full_auto与旧gold_full的partitionquantiles内容逐字相同，只追加shuffle整数分支：从有序精确整数摘要取分界，首尾索引为0与n−1，避开float插值；非整数仍走旧逻辑。这是局部根因修法，没有写入实例常量，也接受重复或其它合理整数近似内部分界。16份非noop补丁的SHA、静态应用、AST均通过，只改生产文件。原1 F2P＋104 P2P名单保留。新正对照仅按本轮真实范围核实，不继承旧gold_full完整资格。

原digest镜像ID `sha256:b4f186ca0a0139f4287b9203a666b9fd009af079ddad700bb2bf8019aede8b99`，HEAD `8663c6b7813fbdcaaa85d4fdde04ff42b1bb6ed0`；Python3.8.19／NumPy1.20.3／pandas1.2.5／pytest8.3.2，无依赖修改。公开原例两端各+1，Python整数比较rc1；公开shuffle为104 passed／3 skipped／2 warnings。三个slow skip不在104参考中，未新增skip。

| 私有候选 | 执行范围与结果 | 准确失败点／通过范围 |
| --- | --- | --- |
| gold_full_auto | 全模块105 passed | v2七组、auto端点/区间/行保留、104 P2P通过 |
| noop／nearest_via_float／clip_partition | 各全模块1 failed／104 passed | 原例1→1最小值+1 |
| gold／uint_only／k1_only／gold_typed_only | 各全模块1 failed／104 passed | 原例1→3最小值+1 |
| gold_full／exact_full／higher_full | 各全模块1 failed／104 passed | 前七组通过；auto首分界…744对真实…743 |
| gold_pin_only | 全模块1 failed／104 passed | 前四组通过；第5组跨2**63的uint64最小值+1 |
| first_last | 全模块3 failed／102 passed | 原例1→3 F2P，加已知旧P2P test_set_index、test_empty_partitions；其余102参考过 |
| rv_pin_noclip | 定向F2P 1 failed | 相邻整数3→5：末端…872越过真实最大…844 |
| rv_interp_pin_noclip | 定向F2P 1 failed | 同组排序断言失败，内值…872大于末端…844 |
| rv_maxonly_threshold | 定向F2P 1 failed | 全负int64：−612509347683174144对正确−612509347683174146 |
| rv_k_le4 | 定向F2P 1 failed | 相邻整数5输出分区：最小…872对正确…842 |

13份全模块各有105状态；4份定向各只有1 F2P，**每份104 P2P未执行**。空p2p_failed不等于通过。first_last两处旧P2P失败为准确记录的负对照，不能报“17份P2P全通过”。四rv候选在各自目标分支真正失败，早期失败的其它候选不能替代它们。

首六份用25文件snapshot `6ed3228ad3615384`、初始13行矩阵SHA `73f3963cf66126e4163ded3f242668b563ee8c790140914fa607b14c27fa0dc2`；后十一份用28文件snapshot `1e59b10771f52f51`。现17行矩阵SHA `de3250c854bb6a5b335812070034eeb0261612344876cba6baca9d84241f1c88` 的前13行等于初始原件，运行未热切。追加作业复用相同公开actor，其attempt/首请求SHA核到，不伪称再次执行actor。

本轮指出的两处作者摘要问题已关闭：results.json旧“剩余待做”状态按追加原件订正并保留历史；cpu_readback准确写明gold_pin_only在跨2**63组失败。同一+1数字不等于同一分支。原CPU输出未改。旧行政暂停记录保留历史，恢复及CPU实际开放以当前回执为准，不从旧暂停文字推导题级缺陷。

## 原件入口与后续停止条件

实际诊断根为 `runs/category2_repair_20260929/swe_dask/cpu_diagnostics/`，上表各attempt的 `remote/readback_manifest.json`、`remote/run/status.json` 为运输及逐参考入口；`remote/run/actor/` 保留真实首请求、trajectory和身份；`remote/run/private/<candidate>/<candidate>/revised_test_file.out` 为完整pytest原件。每份路径、SHA、准确失败行、退出及清理详见同名JSON。runs为忽略产物，交接须连清单保留。

7305关键绑定：revision SHA `b65bf0af180aa373cc663b401d357dbe51d61036a8f065aabfd1ebde95108270`；有效patch SHA `4c63d384f1c62eaa019c12bc70ae8b0cab0d7595e719edcc1d5e878feb86c127`；gold_full_auto SHA `1a249962f60580a4340d6f92a45b414475c0eca86655715abb70229a366b5994`。

本报告足以复用这些版本的题级静态结论与已完成CPU证据，进入已有授权的正式发布交接。后续只需补正式consumer、可信非root评分及逐参考拒绝点窄核；7656核setup900，7138核新增P2P消费，7305完整核17行尤其四rv各104 P2P。材料／配方／公开题面改变时按影响另核；不因换协作流程或摘要修正机械重审全题、重跑已覆盖实验。本轮无新增用户决策请求。

直接原件链接：

- dask7656-cpu-c-20261003-v2：[读回清单](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask7656-cpu-c-20261003-v2/remote/readback_manifest.json)、[逐参考状态](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask7656-cpu-c-20261003-v2/remote/run/status.json)。
- dask9378-cpu-c-20261003-v1：[读回清单](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask9378-cpu-c-20261003-v1/remote/readback_manifest.json)、[逐参考状态](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask9378-cpu-c-20261003-v1/remote/run/status.json)。
- dask7138-cpu-c-20261003-v1：[读回清单](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask7138-cpu-c-20261003-v1/remote/readback_manifest.json)、[逐参考状态](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask7138-cpu-c-20261003-v1/remote/run/status.json)。
- dask7305-cpu-c-20261003-v1：[读回清单](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask7305-cpu-c-20261003-v1/remote/readback_manifest.json)、[逐参考状态](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask7305-cpu-c-20261003-v1/remote/run/status.json)。
- dask7305-remaining-cpu-c-20261003-v1：[读回清单](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask7305-remaining-cpu-c-20261003-v1/remote/readback_manifest.json)、[逐参考状态](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask7305-remaining-cpu-c-20261003-v1/remote/run/status.json)。
