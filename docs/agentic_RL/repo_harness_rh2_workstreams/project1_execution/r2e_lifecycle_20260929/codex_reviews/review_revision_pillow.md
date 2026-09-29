## 结论

| 题目 | 结论 |
|---|---|
| `3ac9396e` | **需小改**：保留 A+B，但还须堵住 K2；A-only 不通过 |
| `3a61c9e9` | **通过，可落正式修订单**；正式评分验收仍待完成 |
| `2b061b68` | **不通过，整题暂挂**：R-f 文案基本合规，但验收缺项且仍有 S1 |

本次全程只读。已重放草案、校验摘要、重新解析 **25 份试跑结果**，并核对相关历史评分、补丁及公开原文；没有新增正式容器评分。

## 1. `pillow__3ac9396e`

### 模板与公开依据

**A、B 都属于 R-c，B 应保留。**

- A：题面描述的是一般的“零分母有理数元数据”，41988 是示例，换一个未登记标签有依据。[题面第 8、16 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605/user_prompt.txt:8)
- B：公开文档承诺按数值类型识别 TIFF 字段；结合 base 的整数编码、解码行为，检查整数读回仍为 `int` 合理。**不固定 LONG/SHORT 编码宽度是正确的，不是为保 gold 放宽要求。**[公开文档第 503–516 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605/worktree/docs/handbook/image-file-formats.rst:503)

两处各针对一个窄问题，符合“多个 S1 分别列依据、同轮修订”。不需要另设授权。

### 验收与三个满分候选

现有试跑结果成立：A+B 下 gold **13/13、得 1**，noop 为 0；K4b、RC6 从 1 变 0，K3、K4 仍为 0；没有 missing／unexpected 键。

但“已经收敛”的结论不成立：

- **K1、K1b**：在本次核心场景下属于合理替代解；公开要求没有固定类型码必须为 5，不能仅因 K1b 使用 10 判错。这不等于所有数值范围都已验证。
- **K2 仍是未处理的 S1。** 最小反例是同一标签包含：

  ```python
  info[65000] = (IFDRational(0, 0), IFDRational(1, 2))
  ```

  K2 要求**所有元素分母都为零**才选有理数类型，因此整组仍落到 LONG writer，抛 `struct.error`。[候选第 9–11 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_actor_20260925/grader_cands/pillow_3ac9_K2_zero_denominator_only.patch:9)

  本次内存执行原 `_setitem` 和字段编解码函数已确认：gold、K1、K1b 保留 `[(0,0),(1,2)]`，K2 报错。公开 API 明确支持值序列；这是**含零分母元数据的同一核心问题**，不是要求全面修复所有非零分母输入。[公开接口第 364–371 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605/worktree/PIL/TiffImagePlugin.py:364)

### 范围与处置

没有答案泄漏，也没有扩大需求；新增期望来自输入及公开语义，不是抄 gold 输出。

**需小改**：保留 A+B，补上述混合序列的窄断言，修正 plan 中“K2 合规、仅属 S2”的结论。验收应确认 gold／K1／K1b 为 1，noop／K2／K3／K4／K4b／RC6 为 0。新增反例目前只有原函数证据，须补完整往返及正式评分。

**A-only 不通过**：它明确留下 RC6 的已知 S1。

## 2. `pillow__3a61c9e9`

### 模板与公开依据

四项均正确使用 R-c：

- 调用前快照：题面要求保留“original”调色板，不能调用后再读取已被改变的参考对象。[题面第 27 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07/user_prompt.txt:27)
- 实际渲染保留 alpha：公开 C 转换路径确实读取调色板第四分量。[`Convert.c` 第 1144–1152 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07/worktree/src/libImaging/Convert.c:1144)
- 非恒等重排：公开 docstring 明示 `[1,0]` 交换两项。[`Image.py` 第 1856–1861 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07/worktree/src/PIL/Image.py:1856)
- GIF 回归：实际调用者传 RGB `source_palette`，并在优化保存时调用 `remap_palette`；第 511、536、657 行均与方案相符。[`GifImagePlugin.py`](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07/worktree/src/PIL/GifImagePlugin.py:511)

### 验收、范围与结论

- 试跑：gold、C1、A1u 均 **73/73、得 1**；noop、W1、W2、W3、W5 均为 0。失败分别落在预定断言，没有键集缺失或环境失败冒充拒绝。
- 正对照仍是 gold；C1、A1u 用于检查没有误拒不同实现。补丁核对支持其不同 alpha 写回／补齐方式。
- 期望来自调用前快照、交换关系和输入颜色计算；没有固定补齐长度、未使用项 alpha 或 GIF 文件字节。未放宽旧断言，没有泄漏或需求扩张。

**通过，可落正式修订单。** 随后在正式材料、镜像和权限下复验上述对照；目前不能称正式验收或探针准入已完成。

## 3. `pillow__2b061b68`

### statement_edits 是否合规

四条 edit 的内容基本符合 R-f：

| Edit | 判断 |
|---|---|
| 1：改标题 | 第 1 类：纠正 base 已有 `formats` 的错误前提 |
| 2：改描述 | 第 1 类：改为真实缺失功能，保留原有“限制格式”目标 |
| 3：删除 save／show 示例段 | 第 1 类：对应错误症状已有 base 实跑反证 |
| 4：改 Expected／Actual | 第 1＋3 类：纠正冲突示例、补有公开依据的 API 约定；Actual 不属于“删除答案”类 |

base 日志确实显示无 `formats` 参数、保存及无参 `show()` 正常。[实跑第 122–129 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_env_repair_20260924/p4/dev_probe/pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8/agent_probe.log:122)

list／tuple、None、TypeError 的引用原文和行号也成立，但它是**后续版本 API 文档**，只能作为自建修订题的依据，不能反称原题解题者本来就应知道。[第 2938–2949 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/worktree/src/PIL/Image.py:2938)

没有写入隐藏测试特有输入、断言文案或实现答案；严格限制读法已获 §11 授权，无须重新选择任务目标。

### 验收尚未满足

- **缺少新公开读者验收**；本次已经看过私有材料的复核不能替代。
- 四处替换均唯一，题面前后摘要相符；评分材料确实不变。
- 历史 gold 为 **55/55、得 1**，noop 为 0，P1 回退解为 0。修订后 P1 的拒绝有题面依据，但这些旧评分不证明新版题目的完整语义已合格。

### plan §6 的两处 S1：均成立，且不止这两处

1. **P2 成立**：正式评分为 1，但新进程默认打开 PNG／TIFF 失败；已有原始日志支持。[P2 新进程证据](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_actor_20260925/grader/pillow_fresh/P2.json:5)
2. **P3 成立**：正式评分为 1，却让无参 `show()` 告警，违反公开旧测试；`pytest.warns(None)` 的提前失败掩盖了回归。[公开测试第 763–773 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8/worktree/Tests/test_image.py:763)
3. **gold 的未注册格式路径也不能仅登记 G1 后放行。** 方案把 TIFF 当作未预加载格式有误：JPEG 插件会导入 TIFF。[`JpegImagePlugin.py:42`](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8/worktree/src/PIL/JpegImagePlugin.py:42)

   真正的反例可用公开支持的 PCX：gold 下新进程执行 `Image.open("Tests/images/pil184.pcx", formats=["PCX"])`，在插件未注册时抛 `KeyError`。本次原 Python 路径核对已复现，显式导入 PCX 插件后可以识别；使用了 C 扩展占位，未做像素解码或正式评分。这违反修订后的通用格式限制要求，应按同一核心要求的 S1 处理，而不是排除该格式保住 gold。

### 处置

**整题不通过、暂挂；R-f 文案方向可保留。**

恢复条件：补新公开读者；修正 TIFF 依据；合并处理上述核心漏测。警告测试兼容修复及期望状态变更按 R-a／R-c 验收。若合理的新断言使 gold 失败，应采用**独立核实的替代正对照**，不能收窄题面。随后完成版本化和正式评分；不能沿用“R-f 后即为训练候选”的旧结论。