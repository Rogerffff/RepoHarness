# pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605：静态审查卡

私有主审，2026-09-25。前稿见 `analysis_before_history.md`，历史对照见 `old_findings_delta.md`。

## 1. 目标与用途

- **版本**：Pillow 3.1.0.dev0，base `48e4e072`。
- **题目**：给未注册的 TIFF 标签 41988 赋值 `IFDRational(0,0)`，再用 raw 方式保存，会抛 `struct.error`。修复后要能保存，读回 `tag_v2[41988][0]` 仍是 0/0。
- **根因**：`TagInfo` 的默认 `type=4`，导致 `_setitem` 里的猜类型分支执行不到，未注册标签一律按 LONG 写出。**这与分母是否为 0 无关。**
- **建议用途**：开发诊断用的静态候选，不需要修订。

## 2. 关键映射

| 需求或旧行为 | 公开依据 | 测试键 / 决定性断言 | 覆盖 | 执行证据 |
| --- | --- | --- | --- | --- |
| 41988 存 0/0，raw 保存不报错 | 题面 Example / Actual | `TestFileTiffMetadata.test_exif_div_zero`：`save(...)` | 覆盖 | noop 5 次 ERROR、gold 5 次 PASSED，共 3 个 build；报错与题面逐字一致 |
| 读回 `[0]` 的分子、分母都是 0（因此必须写成有理数类型，读回形状必须是元组） | 题面 Expected，及示例中的 `[0]` | 同一个键的两处 `assertEqual(0, …)` | 覆盖；不限定类型码 5 还是 10 | 私有 gold 对照打印 `0 0`；K1b / K4 待实跑 |
| 非零分母、其它未注册标签 | 由根因推知，题面没有要求 | 无 | 缺失（题面范围外） | base 上 1/2 失败，gold 修复后正常（devcheck） |
| 显式 tagtype 优先；已注册 RATIONAL 往返；v1 API 的 `(num,den)` 形状 | 公开旧测试 | `test_rt_metadata`、`test_write_metadata`、`test_read_metadata`、`test_ifd_rational_save` | 覆盖（回归键） | 全部 PASSED |
| 未注册整数标签写成 LONG | 公开材料没有约定 | 无 | 缺失；gold 把它改成了 SHORT | 静态推断 |

## 3. 八方面

- **已查**：
  - 题面与提示；
  - 隐藏测试、helper、runner 全文，并与公开测试做了 diff；
  - 目标键的调用链追到 writer 与 loader；
  - gold 及 `TagInfo` 的所有使用者；
  - devcheck（正式启动链，agent 身份）和私有 gold 对照；
  - 5 组 noop / gold 运行，加 M3 的 gold；
  - 两份跨题扫描，并逐个打开 6 个同仓工作树核对。
- **未查**：
  - K1–K4 还没实跑；
  - 模型实际收到的消息，以及真实模型求解；
  - JPEG / MPO 写 EXIF 的路径；
  - `install.sh` 与 pyc；
  - 共享控制面。

## 4. 问题与证据层次（均为低严重度）

1. **题面把原因归到"零分母"**，有误导性，但不构成冲突。证据是镜像实测：base 上 41988 写 1/2 同样失败，282 写 0/0 正常。
2. **测试只覆盖题面的字面例子**：只特判零分母、或只注册 41988 的修复也能得 1。目前是静态推断，由 K2 验证。
3. **gold 附带行为变化**：未注册整数标签的类型码由 LONG 变为 SHORT，读回的值不变，没有测试覆盖。静态推断。
4. **提示指定的运行方式有噪声**：提示要求用 `python -m pytest`，但 Pillow 3.1 的 helper 与 pytest 8 不兼容，写临时文件的用例会恒定假失败，在三份 TIFF 相关文件中占 9/42，base 与 gold 两侧相同。在 `/testbed` 下改用 `PYTHONPATH=Tests python -m unittest …` 则全部通过。证据是镜像实测。
5. **跨题包含**：本题的修复和两个新增测试，出现在同仓 6 题（Pillow 8.0–10.1）的公开初态里。划分数据集时应把它们当作同一族。
6. **`test_ifd_rational_save` 依赖 libtiff**：来源宿主机缺 libtiff 时这个键是 ERROR，当前镜像里有 libtiff。今后重建镜像时要保留 libtiff。

期望里没有 FAILED / ERROR 键，所以不存在"更完整的修复反而被判 0"的风险。另外，隐藏测试用的是自带的 helper，不依赖候选能修改的测试辅助文件。

## 5. 建议、与历史的分歧、唯一下一步

**建议**：处置为 needs_review，理由是"静态候选，待 actor 验证"；不修订材料。可以考虑在环境说明里注明第 4 条的噪声和可用的替代运行方式。

**与历史的分歧**：

- 历史结论 `environment_qualified` 只覆盖环境资格，本轮补上了第 1、2、3、5 条。
- 历史的"提示与无 pip 矛盾"在当前 v3 提示下已经过时。
- 历史记的 pytest 噪声（本卡第 4 条）问题更大了：v3 提示现在明确要求用 pytest。

**唯一下一步**：用正式评分代码在 derived9（`c9ec14f7…`）上实跑以下 4 个候选。

- **K1（合理替代解）**
  - 改法：在 `PIL/TiffImagePlugin.py` 的 `ImageFileDirectory_v2._setitem` 中，于 `if tag not in self.tagtype:` 之下、原 `try:` 之前加一段：若 `tag not in TAGS_V2`、`values` 非空且全是 `IFDRational`，就令 `self.tagtype[tag] = 5`；否则走原逻辑。不改 `TiffTags.py`。
  - 预期：得 1（11/11），没有不符的键。
  - 变体 K1b：把 5 改成 10，预期同样得 1。
- **K2（可能蒙混的部分实现）**
  - 改法：位置同 K1，条件改为：`tag not in TAGS_V2`，且所有值都是 `denominator == 0` 的 `IFDRational`，才设为 5。
  - 预期：得 1（11/11），没有不符的键。但 `info[41988] = IFDRational(1, 2)` 保存时仍会抛 `struct.error`。
- **K3（错误实现）**
  - 改法：只给 `PIL/TiffImagePlugin.py` 的 `IFDRational` 类加 `def __index__(self): return int(self._numerator)`。
  - 预期：得 0。`TestFileTiffMetadata.test_exif_div_zero` 应观测为 FAILED（期望 PASSED；`AssertionError: 0 != 1`），其余 10 个键 PASSED。
- **K4（满足题面文字、但违背题面示例的候选）**
  - 改法：只在 `PIL/TiffTags.py` 的 `TAGS_V2` 里加一行 `41988: ("DigitalZoomRatio", RATIONAL, 1),`。
  - 预期：得 0。`TestFileTiffMetadata.test_exif_div_zero` 应观测为 ERROR（`TypeError: 'IFDRational' object is not subscriptable`），其余 10 个键 PASSED。
  - 变体 K4b：把长度写成 0，预期得 1。
