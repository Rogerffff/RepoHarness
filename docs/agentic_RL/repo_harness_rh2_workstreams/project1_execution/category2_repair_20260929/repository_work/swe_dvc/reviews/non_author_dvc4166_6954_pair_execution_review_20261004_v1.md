# DVC4166/6954 双模型首轮：非作者执行证据窄核

审查日期：2026-10-04 SGT。结论：两份pair回执的执行与评分声明和原件一致，未发现新增执行阻断。4166：Coder raw0、Qwen raw0；6954：Coder raw1、Qwen raw1。新增Qwen两臂均完整完成求解及原FrozenPatch评分、actor/grader清理通过。此处只核执行证据，不把分数当候选语义判断；Qwen七维语义复核另存，当前不替题主ACK、关闭请求或授予训练资格。

审查者已有私有材料和旧Coder上下文，不是fresh公开读者。仅本机标准库读回原件、SHA、tar、JSON、完整日志/SSE与轨迹的执行结束事实，没有运行模型、测试、评分、Docker/SSH，也未改作者材料或总账。事件UTC为2026-10-03 16时段，对应SGT2026-10-04零时段。

## 新原件与复用边界

`P`指本包，`B=runs/ordinary_gpu_probe_20261002`。新增Qwen根为 `B/closed_snapshots/gpu1003-dvc{4166,6954}-qwen36-a1`，本臂结果在各根 `queue_qwen_next12_v1/results/<job>`，live capture在 `diagnostics/QUEUE_QWEN_NEXT12_V1_<job>_before`。路径模板仅用于导航；同名JSON给出精确路径及完整SHA。

两份pair回执实际SHA分别：4166 `4a3ca04aac2f0bd8c10ec5b5c6928643e2c20d2e460cf73365472d4b00f6739d`；6954 `2fa10dbdc3bcfd30e370257003dacc6027df1905f52c48e2182936e12d4d66fb`。逐项核回执引用的execution receipt与Coder/Qwen manifest SHA，不只信回执声明。

新增4166闭合manifest SHA `0640ad8ab7aae12c36a1bd237ad9c8d392630e07df6e39547fac022ac178f563`，其435项/41970853B逐成员SHA、大小无差异；6954 manifest SHA `bd843943fc06ef80cc0fead6fac8eacab228f0ab5bd1317177fb1756fda2c535`，417项/36635646B同样无差异。数量分母是manifest列明成员；父封包也含其他题冻结输入/历史终止辅助原件，并非435/417都是该候选运行文件。本次不审其他题语义。

Coder执行复用 `B/reviews/closed_four_execution_non_author_20261003_v1.md` SHA `5016cc6212911a74f0cffde7bb5d68db783acf56f5078b51d9c52ead9bfb3595`，其JSON SHA `52f447ad6c7dde3aca1f31da54b2c26d35e8e3aa6a661758dcaf05d9315db661`；Coder语义复用 `P/reviews/non_author_dvc_three_coder_a1_semantic_review_20261003.md` SHA `f67401f24fc7a60bd8a2f3a1e2f62c34e5b4e77d0faf86452cbe4c2a2a134a05`。两题旧manifest实际仍为回执给定的46bc255f…与da13b8e…；新pair引用的旧reverification receipt也匹配。本次比较两模型实际attempt/input/prompt，不重读已核Coder全653/600成员、完整轨迹或重评分。旧报告中9395等历史边界不在此次更新范围。

## 实际评分与逐参考

从新增完整eval.log的pytest状态行独立重建，不用receipt observed_map或diag总数作节点分母；所有节点及状态/日志行号在同名JSON。没有skip、missing、unaccounted、重复节点或收集错误。

|题目/模型|实际节点|正式参考|F通过/总数|P通过/总数|额外节点|安装/test退出|raw|
|---|---:|---:|---:|---:|---|---|---:|
|4166 Coder（旧核复用）|66|63|0/3|60/60|3通过|0/1|0|
|4166 Qwen（新增）|66：64通过/2失败|63|1/3|60/60|3通过|0/1|0|
|6954 Coder（旧核复用）|26|15|3/3|12/12|11通过|0/0|1|
|6954 Qwen（新增）|26：全通过|15|3/3|12/12|11通过|0/0|1|

正式F/P计分分区在下表。4166不使用9395的40参考分母；6954也不把26执行当15参考。

|新增Qwen分区|4166|6954|
|---|---|---|
|bound_source_f2p|1项失败|1项通过|
|added_f2p|1通过、1失败（2项）|2项通过|
|bound_source_p2p|59项通过|12项通过|
|added_p2p|1项通过|0项|
|正式参考合计|61通过、2失败/63|15通过/15|

4166的bound F `tests/func/test_ignore.py::test_ignore_file_in_parent_path[data_struct2-pattern_list2-result_set2]` 在eval.log第719—725行行为断言失败：实际仍有dir/subdir/should_ignore，期望空set；added F `test_directory_rule_prunes_directory` 第746—752行断言not dvc.tree.isdir(blocked)，实际True。第三F（added）`test_negated_directory_rule_recovers_non_example`通过。两个失败均是真实行为AssertionError，不是导入/收集或安装错误。FAILED状态第1149/1150行，footer第1151行为2 failed/64 passed；diag num_parsed_tests=66，原report unresolved/tests_failed、F1/3、P0fail/60，raw0正常。

4166额外3项 `test_dvcignore_in_out_dir`、`test_match_nested`、`test_ignore_external` 全PASSED。6954额外11项全为func params/test_show.py的原公开测试（完整ID见JSON）；26状态第1513—1538行全PASSED，footer第1539行为26 passed/112 warnings，diag parsed=26、RESOLVED_FULL，report resolved/raw1。两题原report/result/status内容相同，逐分区与完整日志一致，不改任何评分。

两题真实安装marker分别eval第666/716行RC0；真实test marker第1155/1543行为1/0，段完整非skip/partial，无install_failed_commands。外层candidate_exec_exit_code均0，因为single-shell最后echo标记返回0；不能据此外推4166pytest通过。实际候选前提检查记录user54322、HOME rh2grader、exit0和UID54322离线wheel字节预检标记；trusted setup原UID0标记同时存在。actor可信初始化AGENT_UID54321和测试临时目录pytest-of-rh2grader一致，但不把stdout本身提升为不可伪造独立UID硬件证明。

## 原FP、baseline、材料及公共输入

原FP canonical独立重算：4166 `sha256:90b6ce6e6b04ef062b40b34bc4192a91750ee98d8e2e719c8c47725475565867`；6954 `sha256:1bcd6de39c9ad447208100b8c023afd361a248beaf5f073d74a10f262639f487`。逐entry解码content_b64并核content_digest，原件自洽。

4166完整FP有两项：dvc/ignore.py与tests/unit/test_ignore.py；实际projection只含业务ignore.py，官方测试修改被剔除，applied_entry_set重算 `sha256:52a85ee1b5cd7b97712c719027369c86cd8d3627f232e1fd82537345fe97677f` 等于report hygiene。其新增自测不能当作正式评分测试；完整FP两项身份保留。6954只有业务_py.py一项，projection同一项，applied_entry_set重算 `sha256:6498afee260583403cccf09a382392387ae2e254864e9cb12e14c8cfcd46caa8` 一致。hygiene clean的digest不是完整FP artifact digest。

baseline canonical分别 `sha256:16f108c365097d36390d40ff2b06c47fcf186b13c0e4cae2381ebfe6048ab6db`、`sha256:be0c03047652bd7c8ac13b696722f056a7b498ca5dd3c12fceba519a642c8625`，与同题Coder相同。分别430/552个baseline项逐类型/mode/SHA与baseline.tar及grader重建census匹配，无多缺/值差异。4166保留原镜像setup.py已知metadata dirty；615等计数属于9395，未混入本题。

实际actor/diag grader镜像：4166 `sha256:28ed5ef69d46c326ec183f8719e426611ca848046156fa98f9f6c7f35b46ebeb`，base520e01f11305aba1994df354adef86e6d90180de；6954 `sha256:083832998996245f4f49eaab3f5f9314fe9fe23bafda7fc9641ae8cec6803c30`，base28dd39a1a0d710585ff21bf66199208b1b83cbde，均与同题Coder绑定一致。实际采用local_build镜像；公开bundle中的registry manifest身份不冒充实际容器Id。新source_manifest实际为原code8 SHA `09ddb8bfdeecd3ffaa38c1048a574161ef6fa6053b2855da50166e8e8677899d`，关键entry SHA `bdf806bf8da1d5ebb4970887bfc3c7738eb3e57a75e1d07215d6d68b17e574c4` 不变。

同题两模型input_check的budget/public_delivery/assignment/baseline_policy/prepared_manifest/host artifact/材料/revision/grading budgets/runner/spec overrides相等；solver、attempt及服务配置不同，不声称整个input_check文件同字节。材料4166 `sha256:f8b06581558ea281d57125a23fe9820da7200ce4e96ac0eb5533cc5e1aa7735c`、6954 `sha256:77a22ff0a47782cb689525fc0ac48a7b2828bf931b17c887ea0d42683e067bfa`；revision分别behavior-v2/v1-draft，预算whole/setup/apply/test=3600/300/120/1800。scripts_digest同题与Coder完全相同，4166 f17acd23…、6954 d8b83fd2…。restore/apply均成功，保护的两测试无missing/irregular，候选不能用所改official test改变评分。

同题solver_prompt Coder/Qwen字节完全一致：4166 SHA `f8e4a0203d4451e12190e55247960ca8b95dd005e3d5cf5b8e17c4de125c99fc`；6954 `5fdfe964e45d2c71264afc4c43542e1a778e173d75addd4039cbef861cf7fc98`。首个gateway请求用户正文分别逐字等于完整solver prompt，原issue CRLF44/74处保留；原公开problem_statement在正文中原样出现，中性brief同题相同，不暴露私测。CC同时附有独立currentDate system-reminder，不把它说成题面字节变化。

## 实际服务、profile与结束证据

直接递归比较两模型attempt.profile_parameters，每题唯一差异确为network.model_proxy_upstream：Coder18081、Qwen18082。其余profile参数相同，包括actorUID54321、2CPU/4GiB/PID512、无额外swap、/tmp1GiB、独立internal网络/relay和只允许模型代理。这是profile对象的范围；两模型服务、sampling/parser/checkpoint不等于“全runtime仅端口不同”，也不作速度或能力因果排名。8GiB writable quota是配置且require=false，不伪称实际强制quota已验证。

新增Qwen各自在job启动前约0.1—0.3秒完成live capture：engine/adapter before/after inspect Id、Pid、StartedAt、RestartCount相同，running且restart0、模型mount只读/model。actual engine argv为SGLang bfloat16/tp1/context196608/max-running1/mem-fraction0.90；actual HTTP server_info ready、context196608、max_req_input_len196602，与配置匹配。adapter argv接30001、服务18084，tool parser qwen3_coder/reasoning qwen3、idle14400；实际配置sampling temperature1/top_p0.95/top_k20/output65536，网关18082转接18084，force_model Qwen3.6-35B-A3B、retry0。这些是实际service链证据，不靠响应中的slime-actor别名识别checkpoint。

checkpoint下载manifest SHA `32bd30f61860366b3783eabc9d75bee0cd28c474d9c07de8be8d9ae60a4552ab`，repo Qwen/Qwen3.6-35B-A3B、revision995ad96eacd98c81ed38be0c5b274b04031597b0；identity binding SHA `603bec65f047c9b87967c58be43b8933ef3b662f9eab7052ac8ee64c3ae9e9f7`、chat template SHA `e84f32a23fdda27689f868aa4a1a5621f41133e51a48d7f3efcbea2839574259`。manifest files_count=40而files数组只有37；actual model_file_sizes也37，逐文件名/大小匹配，其中26个safetensors分片，总列明大小71926788362B。本次capture未逐权重新SHA，也没有GPU内存权重attestation；不能称40文件完整新验或37权重。列明manifest/live mount/argv/HTTP绑定足以支撑本次执行身份记录的有限范围，这个限制保留，不触发机械重跑。

模型预算同题均196608 context、65536 output、240 CC turns、10800秒solve、1024请求、first-byte1800、idle14400。独立读gateway全部66/43请求及对应66/43 SSE：seq连续，无缺响应/重复序号，每个恰有message_stop且无error事件，最后end_turn，其余tool_use；model_sent均Qwen3.6-35B-A3B、请求max_tokens均65536。响应slime-actor只是公开协议别名；CC modelUsage里的maxOutputTokens32000也是元数据，不能直接替换实际请求65536。实际SSE记录最大input53374/29352低于本次live上限，不把累计tokens当context峰值。

完整轨迹1055/609行JSON可解码，各一个success/is_error=false/completed result；harness真实RC0、无partial，actor gateway close均revoked=true、active_requests0、drained=true。actor rm0、container/relay/network残留空；grader manager created=removed1/1、open/supply/failures空，cleanuptrue。共享engine/adapter保持运行不属于本job清理对象。

退役unit读取为not-found/inactive，默认ExecMainStatus0不能证明退出。两job各有精确PID1 journal的Started与Deactivated successfully（4166 16:09:35.509256Z，6954 16:15:03.215237Z），且原registered request SHA、attempt/result SHA与journal辅助success记录匹配，原dispatcher completed RC0；使用这个闭合链，不拿别题历史成功事件代替。request registered SHA分别80a54486…/f0c212d6…，与题主原请求SHA0425400c…/b0eede7f…是不同文件，已核两组owner原件副本SHA相同。

资源monitor声明分别35/22样本但有采样缺口；官方diag.resource_facts仍null，peak_memory_mb仅沿用原diagnostics1118.684/1017.27，不授予全程OOM/PID/峰值独立证明。cleanup与完整执行不自动授予正式环境/训练资格。

同名JSON SHA256 `74b992760a01bd59adbded9096c9029ee297e5118206b23f4db017e5046e0df8` 包含全部92实际节点与证据完整SHA指针。当前两份pair的执行声明可核收；作者Qwen七维结论仍待另核，不改变semantic_acceptance=null、请求未ACK和单次首轮的不稳定性边界。
