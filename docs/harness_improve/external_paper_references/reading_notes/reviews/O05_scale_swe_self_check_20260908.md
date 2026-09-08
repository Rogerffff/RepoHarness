# O05 ScaleSWE v4：作者自查、访问缺口与合成探针

日期：2026-09-08。正文：[O05_scale_swe.md](../O05_scale_swe.md)。

**状态：主体文本精读与官方资产／代码定点检查已形成；附录E、原图页与PDF页码仍待补，不标完整全文核验通过。** 本次仅作者自查，没有独立reviewer，也没有执行模型训练、真实ScaleSWE镜像或官方完整评测。

## 1. 固定版本与检查范围

主论文：*Immersion in the GitHub Universe: Scaling Coding Agents to Mastery*，`2602.09892v4`，2026-03-24。主读官方HTML全部正文、References、附录A–D可读部分；Table1–5全部HTML行列，Eq.(1)–(3)，Fig.1–5图注与邻文。HTML附录E只有标题和残留反引号，不是已读全文。

官方ScaleSWE仓库固定`b531926bf4fc069451eca390587a4e30c1b1bb21`；AweAgent固定`b38414e5dc9c7c51f2ec48318b718af0c8852060`。实际源码范围是正文C1–C7链接；没有整库审计。HF数据卡、viewer、Files和公开commit线索已读，但未下载984MB任务文件或4.72GB轨迹、未拉镜像、未遍历训练／评测轨迹。

项目阅读基线`bbce8683b025077ac1bed5da7d7587a6f1ec8dcb`，分支`miles-migration`。本线程仅维护O05正文及本记录，不修改共享README/catalog、B的请求、训练代码、数据集或实施定案。

## 2. 原文访问问题与不该推定的内容

| 材料 | 实际状态 | 本稿处理 |
| --- | --- | --- |
| v4 HTML正文 | 成功取得，436个解析行 | 通读正文／引用，按章节、表、公式定位 |
| PDF v4 | 浏览器返回文件过大，10,949,149 bytes；其他入口亦失败 | 没有可用PDF文档对象，不能声称已截图或核对物理页 |
| 本机PDF下载 | requests域名解析失败；下载工具失败 | 没有伪造本地PDF或可下载链接 |
| Fig.1–5及作者文章PNG | 直接获取失败 | 保留图注与作者文字解读，不从图猜数据 |
| Appendix E生产prompts | HTML渲染缺失，PDF/TeX未取得 | 明确“本轮未取得”，不写“作者未公开” |
| 当前官方solver prompt | 并非历史生产prompt | 不用于填补EBA/UCA/PSWA附录E |

后续补核需要原始v4 PDF或TeX，重点是EBA/UCA/PSWA提示词的工具、retry、budget、状态转换与停止要求，然后对Table1–5和Fig.1–5原图做一次目视核查，补物理页码。无需从头重写已明确的主体、资产与代码部分。

## 3. 关键数字和解释的自查

| 项目 | 易发生的误读 | 本稿保留的正确边界 |
| --- | --- | --- |
| 100k / 20,181 | 把构建成果当作已公开任务数 | 100k为论文成果；20,181为本轮可读HF页面行数 |
| 25k / 71,498 | 将轨迹数当成独立任务数 | 每题5次计划；成功轨迹可重复对应任务 |
| 3.5B / 3epochs | 直接当成10.5B实际loss token | 数据序列token、实际截断/packing和目标mask未完整披露 |
| 60% / 64% | 静默修正引言或替作者解释原因 | v4引言60与表3等64同时记录，主结果按表3 |
| Table4 54.8/54.6/64.0 | 相同pipeline意味着同token、同有效轨迹、同费用 | 这些分母没有给齐；SWE-Gym/SWE-smith0.2pp无统计显著证据 |
| SFT / RL / OPD | 测试筛选成功轨迹等于RLVR | 本文是教师轨迹SFT；未报告online RL或OPD |
| 131k / 262k / 100turn / 200turn | 将训练、教师、评测与后来README预算混合 | 各阶段分别列，现代复跑配置不回填v4 |
| 94/100人工有效 | 4名审查者等于每题4人一致、全量94% | 只记录作者披露的抽样与有效数，协议细节未给 |
| f2p_patch / f2p_script | 两个字段互斥 | 论文B文字、HF实例与当前同时布置的实现分开记 |
| 61.4%复跑 | 未改动main可完整复现64% | 文档自述评分补丁、cleanup与未发布runtime配置依赖 |
| 现代test runner | 有JUnit匹配就每次都检查全部expected ID | true-marker fast path和summary fallback接受条件较弱 |
| Git清理 | 已完全阻断网络／所有信息通道 | 只按所示script描述本地Git历史处理，非完整沙箱安全保证 |

算术检查：

- `100000 / 6000000 ≈ 1.67%`，`100000 / 1000000 = 10%`，仅为粗略阶段产出比。
- `71498 / (25000 * 5) = 57.1984%`，只对应名义采样计划，不是学生通过率。
- `3.5e9 / 71498 ≈ 48952`，粗略序列token/成功轨迹，不是assistant有效token。
- `64-22=42pp`、`64-51.6=12.4pp`、`64-59.2=4.8pp`、`64-62.4=1.6pp`。
- `64-54.8=9.2pp`、`64-54.6=9.4pp`；`307/500=61.4%`，不能用498作官方所报分母。

## 4. 已执行的合成pytest探针

### 4.1 问题和范围

当前`aweagent/core/eval/utils.py::run_tests_with_runner`在看到`<pytest>true</pytest>`时直接返回True；其runner在`pytest.main(...) == 0`时打印该标记。JUnit的逐expected ID检查只在后续分支。

本探针只检查“pytest返回0是否能包含未执行的expected测试”。没有运行真实数据集、完整AweAgent RuntimeSession或任何模型，没有修改上游仓库。

### 4.2 可重现代码

在临时空目录创建：

```python
# test_demo.py
import pytest


def test_ok():
    assert True


@pytest.mark.skip(reason="synthetic probe")
def test_skipped():
    assert False
```

再执行以下独立runner（参数与所查上游runner一致）：

```python
import pytest

ret = pytest.main([
    "-vv", "--junitxml=results.xml", "-o", "addopts=", "--rootdir=.",
    "test_demo.py::test_ok", "test_demo.py::test_skipped",
])
print("<pytest>true</pytest>" if ret == 0 else "<pytest>false</pytest>")
```

本轮环境设置`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`，避免加载无关第三方插件。Python3.13.5，pytest9.0.2。实际输出与XML解析摘要：

```json
{
  "probe": "one-pass-one-skip",
  "python": "3.13.5",
  "pytest_version": "9.0.2",
  "expected_test_ids": [
    "test_demo.py::test_ok",
    "test_demo.py::test_skipped"
  ],
  "testcases": 2,
  "skipped": 1,
  "status_marker_true": true,
  "all_expected_executed_and_passed": false
}
```

### 4.3 能说明什么，不能说明什么

这在本地版本上证实：true-marker条件弱于“每个expected测试执行并通过”。结合固定代码的fast path，可以形成一个需要在目标镜像验证的评分边界。

它**不证明**ScaleSWE论文历史评分器同样实现、不证明真实任务中skip可由模型操纵、不证明64%分数受影响，也不证明所有pytest版本／插件组合行为相同。移植代码前应在目标环境核查真实测试语义，而不是用这个小实验替代整套数据质量审计。

## 5. 文档检查与实际未做事项

本地已检查引用式链接定义、章节导航锚点、数学分隔符、UTF-8、无替换字符、无行尾空格，以及上述算术与合成测试。自查时修正了§8.1图示：应先调用继承的evaluate组织session/setup/patch，再调用子类run_tests，不能把继承关系排成相反的执行顺序。表值以原文HTML逐项对照，仍待PDF原表核验。

本稿没有独立reviewer、没有虚构线程ID或审查工具；没有训练、GPU实验、镜像拉取、全量去重、真实gold/no-op/替代解验证，也没有上传原论文或第三方代码缓存。阅读笔记不是项目环境准入证书。

写入远程时只新增本记录与O05正文。具体提交、文件完整性回读由交付回复报告，不在提交前预填commit。后续独立复查应优先补原图／附录E、核查Table4因果边界、HF字段与实际评分路径，而不是再写一份只复述100k和64%的摘要。
