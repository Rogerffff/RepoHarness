# EA69 新公开交付 wrapper：非作者静态窄核

2026-10-03。**当前字节版本通过非作者静态窄核；空候选约束已修正。** prompt拼接、任务身份、继承/import/env与E2E Namespace未见实际接线错误；原求解、导出、评分、往返和清理调用均保留。新statement正式发布尚未完成，脚本尚未执行；本报告不代表CPU运行通过。

仅读本题 `public_notes_cpu_solve.py`、`public_preserve_cpu_e2e.py`、`public_preserve_delivery_v3.json` 和必要父入口。只做AST/syntax、JSON与SHA静态检查，未动态import、SSH、Docker、模型或项目测试。不是fresh公开读者，只新增本报告与同名JSON。

## 空候选约束已修正并复核

`EmptyPublicDelivery`仅继承原`module.E2E`并覆写`solve()`，先调用`super().solve()`完成原求解、导出与收口，再同时要求原candidate的`export_ok is True`、`empty is True`、`entry_count==0`、`entries==[]`及原`attempt/frozen/frozen_patch.json`的entries为空。它记录范围校验、wrapper和FrozenPatch文件摘要；不符时写stop_reason、保存并抛错。父main的finally仍停止endpoints，异常不会进入grade。缺失或畸形FrozenPatch同样抛错，不会继续评分。

这项修正关闭了此前“非空产物仍可按patch-dir完成一般E2E”的范围缺口。它没有改FrozenPatch、强置empty或手填noop；通过校验的原空导出才进入父正式noop、往返和残留检查。未发现需要继续修正的实际接线问题。

## 已核通过的接线

- `PublicNotesAttempt`只覆写solve，替换已加载模块的`R2EAttempt`全局名；父`main/_amain`实例化该类。`super().solve`沿原`sa.Attempt`启动真实ClaudeCodeDriver；run、preflight、baseline、export、cleanup没有覆写。
- prompt为原prepared prompt加ordinary_gpu入口相同拼接常量和`notes_text.strip()`，只`dataclasses.replace(task_spec, prompt=prompt)`。其他任务、镜像、材料字段原样传入。精确核EA的task_id，不读取不存在的instance_id；固定statement全文需已存在于父prompt。
- release manifest、notes与statement有摘要校验；notes非空并经过禁止标记扫描。delivered/base prompt摘要、wrapper及冻结solve身份写入attempt；prompt文件在父run初写后由本solve更新，随后父solve直接把更新后的spec.prompt交给driver。
- E2E加载固定release源码，新solve是独立Python子进程。它继承E2E.base_env复制的`COVERAGE_PUBLIC_*`，设置固定CC平台包；在进程内插固定release的rh2/src。父r2e入口插base_probe路径，base_probe再插ordinary_probe路径，`solve_attempt/frozen_transport/result_validity/roundtrip`依赖可达。未改容器agent_env/env_injections/profile。
- 原E2E类读取的21个Namespace字段均提供，无缺字段。no_grade=false、controls为空、regrade为空，不跑gold、不跳评分；父grade/roundtrip/endpoints停止/residuals逻辑保持。
- CPU-C的18210/18211是本题已分配固定端口。wrapper直接构造Namespace只绕过父CLI过时18190–18199范围检查，没有新增任意端口参数或资源权限。全机2槽/prepare1仍由原资源入口管理，wrapper不另造调度。
- scenario只有R2E预检与公开compat命令；命令代码体和已验`public_filewrite_compat_v1.py`完全一致，替身修改仅进程内生效，不改项目HTML或测试，不解题。末文本由原build_stub_script补入。
- wall1200/context32768/output4096保持窄验预算；实际3个stub步骤含末文本，父max_turns为6、gateway cap12。grade timeout5400，setup/candidate仍沿父默认300/900，不改正式验收要求。

## SHA 与适用限制

| 工件 | SHA-256 |
| --- | --- |
| `public_notes_cpu_solve.py` | `96353a9700fb99b515056edac2c213667db0bb46e4b768aab6e9ed6fc41d7463` |
| `public_preserve_cpu_e2e.py` | `9302124d5ad280e4041c1f4fba4516db0284d4907ba62e735b371bc002bdd19f` |
| `public_preserve_delivery_v3.json` | `418cc4e5bdd3c56ecb2beea98c6768d64b79300657cec3da22f80fec4b2b54cd` |
| 父`r2e_probe_e2e.py` | `a5b23b49f126b76a1512a3a6f184bb7e16276c4e9cf137dc7cdc46d3af4ee4fc` |
| 父`r2e_solve_attempt.py` | `10a71cca67af24c9ab5a6de09cb1845751c643632559842bb61dbce6ebc01d5a` |

本结论只覆盖上述字节版本。新statement发布后的manifest成员、prepared/public身份仍须核固定实际版本；本轮没有确认未来文件。现有身份guard用assert，运行不得使用`python -O`或`PYTHONOPTIMIZE`。静态核查不能证明实际import、messages_000、预检、空FrozenPatch、49键评分、往返或清理成功。真实CPU结果仍须另做本题独立原件核查，不重复已有效七候选矩阵；本静态报告不授训练资格。

完整证据路径、父调用链SHA及逐项结论见[同名JSON](non_author_ea69_public_delivery_wrapper_review_20261003.json)。
