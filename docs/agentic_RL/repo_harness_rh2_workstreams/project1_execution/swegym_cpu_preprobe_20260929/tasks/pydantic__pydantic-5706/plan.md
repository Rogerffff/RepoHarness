# Pydantic5706：CPU 输入（2026-09-29）

状态：输入已准备、未运行。仅问题定位；当前不能纳入能力比较或训练。

这是两个独立问题：公开题面允许“更早拒绝”与“支持合法 JSON 数组”两种读法（P5）；已有 source-only 映射候选在历史运行中满分却破坏公开 Python Sequence 行为。本次只核后者在当前配方/正式评分的适用性，不用 gold 成功替代目标选择。

`runs/swegym_cpu_preprobe_20260929/task_inputs/pydantic__pydantic-5706/public_commands.json` 包含公开原例的精确症状捕获、range/tuple/deque与旧六参数测试。两个预期异常均明确核类别和字段；rc0只表示原bug复现。Python3.8以typing.List[int]等价适配。

私有候选 `private_source_only_sequence_list.patch` 从精确base重建，只在 SEQUENCE_ORIGIN_MAP 加 collections.abc.Sequence:list。没有复制旧候选的安装元数据和测试修改。`private_quality_experiments.json` 与 `private_regression_commands.json` 规定 base/gold/候选同配方矩阵：正式分数预计0/1/1；公开旧行为预计base/gold通过，候选拒range并把tuple/deque变list。必须确认候选投影、实际加载、完整逐参考与清理，安装/导入失败不算有效拒绝。

恢复见同目录recipe_restore.json：core0.31.0、固定upstream digest、pydantic-install-v1及wheel manifest；新环境仍待root实际验证。历史旧结论不回写。

全部剩余：root完成当前actor与正式矩阵，我归因并修订授权内环境配方；P5目标选择需批量提交用户，不能用后检静默消除；SWE正式题面/测试修订入口尚待成本调查；JSON值保真/负例缺口保留；gold自定义items hooks只属静态扩展疑点；generator文档冲突不增成硬评分；独立复核、公共GPU接线/预算仍未完成。

证据：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/pydantic__pydantic-5706/`中的card/public_read/review/screening_record及历史补证；实际核过题面、base tests/test_types.py:1876–1891、_std_types_schema.py映射、gold补丁、旧candidate.diff唯一生产hunk。历史正式配方记录在`runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-5706/`。
