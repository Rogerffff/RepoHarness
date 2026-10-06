## 结论：需小改

**四项 R-c 的行为目标有公开依据；但第 4 项额外固定了位序，会误拒一种等价实现。修正后再落正式修订单，无需改变 P4 处置或另请用户决策。** 本轮只读，未修改文件、未新跑容器。

### 1. 模板与公开依据

R-c 用对了：四个窄问题分别对应 D、C3、A、B，一轮合并处理符合 §5；不涉及 R-a／R-b／R-e／R-f。

| 项目 | 原文核对与判断 |
|---|---|
| 默认及显式 262=1 | 成立。题面第 7 行要求 “retain the specified photometric interpretation”；[SAVE_INFO 第 1459–1460 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/worktree/src/PIL/TiffImagePlugin.py:1459)明确两模式默认值为 1。不是新增行为。 |
| G4／LZW 压缩路径 | 成立。[公开文档第 906–912 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/worktree/docs/handbook/image-file-formats.rst:906)列出两种压缩；覆盖标签的代码在两条写出路径分叉之前。 |
| 保存前快照、源图不变 | 成立。[Image.save 第 2158 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/worktree/src/PIL/Image.py:2158)写的是 “Saves this image”；结合 base 不修改调用者像素，以及[公开往返测试第 110–122 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/worktree/Tests/test_file_libtiff.py:110)，快照是补齐原比较的前提。 |
| 存储数据符合 WhiteIsZero | **行为依据成立，当前字节断言需改。**公开读取映射第 136–163 行区分反相及位序；[公开测试第 487–518 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/worktree/Tests/test_file_tiff.py:487)比较不同编码下的同一图像。我也核对了相关 TIFF 文件头，标签与草案说明一致。 |

**并进两个已有键可以接受。**奖励仍是完整映射匹配，区分能力不因合并而减少；代价是只能从日志定位首个失败，后续断言会被遮蔽。当前候选矩阵已分别触达四项，正式验收应保留完整日志。

### 2. 验收证据

已独立核对：

- 替换旧文本恰好出现一次；内存重算的新测试摘要为 `179b8ff3…`，与草案一致。
- 62 键及其期望逐键不变；补丁摘要与原件、正式账本一致。
- **试跑：gold、C1 均为 1；noop、D、C3、C2、A、B 均为 0。**
- 首个失败行与报告一致：noop 459、D 476、C3 492、C2 460、A 457、B 468。A／C2／C3 有一个参数的完整回溯被截断，但两参数的失败摘要一致。
- 所有试跑无 missing／extra；其余 60 键保持匹配。D、C3、A、B 的旧版误放行得到纠正，C2 仍被拒绝。

**C1 是合理替代解**：仅处理目标模式与请求值，使用已有 `1;I` packer／`point`，保留默认行为及压缩所需属性，并非复制 gold 实现。**A、B 确为错误解**：A 改坏调用者图像；B 改坏既有 WhiteIsZero 读取行为，后者也有公开测试支持，不依赖争议中的写入语义才能判错。

期望来自输入快照、公开默认值和编码语义，**不是抄 gold 输出**。但试跑不能替代正式验收：修正后仍须重建材料，核摘要、权限、libtiff，并正式复跑完整矩阵。两个 `pytest.warns(None)` 失败是已解释的旧兼容问题，不是本次回归。

### 3. 唯一必改项：不要固定 `FillOrder=1`

[草案字节断言](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/revision_plan.md:97)直接比较：

`stored == bytes(b ^ 0xFF for b in original.tobytes())`

这只适用于当前位序。[第 68 行](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/revision_plan.md:68)称 “FillOrder=2 ……不是合理实现”，**没有公开依据**。

具体反例：在 C1 中，仅把未压缩 `'1'` 路径改用 `rawmode="1;IR"`，同时写 `FILLORDER=2`，其它分支不变。公开代码已有[对应 packer](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/worktree/src/libImaging/Pack.c:549)及[读取映射](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/worktree/src/PIL/TiffImagePlugin.py:138)。它保留图像语义，却会被该断言拒绝。例如原始位串 `0x80`，合法存储为 `0xFE`，草案却要求 `0x7F`。这是源码与内存字节验证，尚未跑候选评分。

**修法：按文件声明的 FillOrder 归一化位序，再比较样本；删除上述无依据排除，并补这一等价实现的正对照。**不能用跳过字节检查来处理，否则会重新放过 B。

P4 可以维持：不做 R-f 不代表允许两套相反像素输出。只改标签、不转换存储数据会改变保存图像的视觉内容，应依据公开保存／往返行为拒绝；但不宜称它必然是“格式不合法”或“标签与数据自相矛盾”。

### 4. 处置

**需小改，不暂挂整题。**修正第 4 项及说明，补等价位序正对照，再正式验收。未发现为保 gold 放宽要求、答案泄漏或新增题面冲突；当前不能直接认定为修订验收通过。