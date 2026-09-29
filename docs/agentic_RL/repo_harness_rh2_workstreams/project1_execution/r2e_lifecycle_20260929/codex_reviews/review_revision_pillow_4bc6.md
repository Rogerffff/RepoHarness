## 结论：不通过，整包暂挂

**新增 R-c 测试本身通过；阻塞点是把题面原例的语义分歧默认降为 S2。** 这应按 P5 交用户裁定，不能以“未决定就选 A”放行。

### 1. 模板与公开依据

**R-c 用对，新增断言范围合理。**

- **真正反相**：题面第 20 行明确要求 “successfully invert the binary image”；源码说明为 “Invert (negate) the image.”，不只是消除异常。[题面](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/user_prompt.txt:20)、[ImageOps.py](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/worktree/src/PIL/ImageOps.py:518)。
- **模式、尺寸不变，输入不被修改**：既有 L/RGB 路径经 `image.point(lut)` 返回新图；`point` 默认保持模式，C 层按原尺寸分配输出。这是既有公开行为的延续，不是从 gold 反推要求。[ImageOps.py:53](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/worktree/src/PIL/ImageOps.py:53)、[Image.py:1696](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/worktree/src/PIL/Image.py:1696)、[Point.c:155](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/worktree/src/libImaging/Point.c:155)。
- **期望值不是抄 gold**：调用前将输入转成 L，再逐字节计算 `255-v`，由规范二值图黑白互换推出；输出也转 L 比较，未钉死原始字节必须是 0/255。
- 两项缺口分别列依据、合入同一窄场景测试，符合 R-c。没有删键、放宽旧断言、改 mock 或题面，R-a/b/e/f 不涉及。

**W1 属第 4 步 S1，判断成立**：正式评分得 1，却修改调用者输入；这是常用行为被破坏，不是边缘路径。

### 2. 验收证据

逐份核对日志与结果映射，确认：

| 候选 | 修订试跑结果 | 失败位置 |
|---|---:|---|
| gold、A1、A2 | 1，25/25 通过 | 无 |
| noop | 0 | 旧 `test_sanity` 与新键 |
| D1 | 0 | 新测试第 490 行：输出未反相 |
| W1 | 0 | 新测试第 491 行：输入被修改 |

六份结果均解析到完整 25 键，无 missing／unexpected；旧 24 键状态不变。D1、W1 原材料正式评分均为 1，故这两项误判确已在试跑中纠正。[试跑证据](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/trials/)

内存重建也确认：旧文件字节不变、475→491 行、期望仅新增一键，哈希分别为 `9bdba0cc…`、`b2a68136…`。

**这些支持草案断言有效，不等于正式验收完成。** 正式材料仍须核摘要、投影与执行完整性；gold 是否能作为整题正对照，还取决于下述语义裁定。

### 3. 阻塞项：非规范输入不能默认 S2

[revision_plan.md:195–206](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/revision_plan.md:195) 有两处问题：

1. **公开依据漏查。** “字节反相没有文档依据”“MAX 未定义”不准确。公开 [ImageChops.rst:20–23](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/worktree/docs/reference/ImageChops.rst:20) 明确写：
   > MAX (which is 255 for all modes supported by the operations in this module)

   配合 `ImageChops.invert` 的 `out = MAX - image`，字节读法确有公开旁证；但不能据此认定它是 `ImageOps` 新支持模式的唯一要求。

2. **不能从“两种读法有依据”推出“默认两种都接受”。** `color=1` 就是题面原例，而且由常见公开 API 产生。gold 输出 254、转 L 仍全白的事实已实测确认。[原复现命令与输出](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_lifecycle_20260929/devcheck_rev/unrev/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/private_control.json)

   这里争议的是**反相后应黑还是仍白**，不是等价存储表示。v1 [P5](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md:79) 要求任务目标分歧暂挂并交用户；“会拒绝 gold／自然写法”也不是降低要求的依据。

新增测试没有扩大需求或泄漏答案；**但当前“默认 A、非阻塞”的处置绕过了尚未解决的核心语义分歧。**

### 4. 修改与恢复条件

- 保留现有 R-c 测试；修正 MAX 的引用及相关结论。
- 将 §7 和 `user_decision_pending.blocking=false` 改为 **P5 待裁定，整题暂挂、仅作问题定位**，不默认 A。
- 用户选 A：明确登记允许该行为的范围，再完成正式评分。
- 用户选 B：补题面原例断言，独立核实 A1 后按 D4 作正对照，保留 gold／A2 失败证据，再完成正式验收。

本轮仅只读核查和内存计算，未修改文件、未新跑容器。