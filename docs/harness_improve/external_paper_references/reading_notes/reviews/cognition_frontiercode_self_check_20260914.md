# FrontierCode 原版与1.1：作者自查及交付记录

日期：2026-09-14。成品：[原版](../cognition_frontiercode.md)、[1.1](../cognition_frontiercode_1_1.md)。

**状态：两篇正文、所给全部技术图表和展开案例阅读完成；作者自查完成。没有独立reviewer，没有真实模型、沙箱、测试或联网检测复现。** 本线程没有启动独立研究子agent的工具，因此不编造线程ID、effort或独立审查通过标签。

## 1. 输入、版本与工作范围

输入是用户上传的 `03_FrontierCode.md/.zip`。ZIP为76个条目，解压内容5,270,134 bytes；检查路径没有逃出目标目录、没有符号链接后读取。主体来源采集于2026-09-11：原版09:47:47.728Z，1.1为09:47:51.919Z。原始发布日分别为2026-06-08、2026-07-07。

本轮两个官方URL均返回可读正文，核了标题、署名、日期、章节与关键表述；没有宣称实时页面和全部动态图表在采集后从未变化。数值与动态案例仍以冻结来源包为准。

远程基线 `miles-migration@506879e07804548ebe84bcec6f4d00fa1d36d03b`。检查阅读目录未发现本轮预定目标文件。只新增两篇正文和本记录，不修改共享索引、批次总数、来源补充包、训练配置、代码、taskset或其他线程成品。

## 2. 阅读覆盖

| 来源 | 主体 | 视觉与动态材料 |
|---|---|---|
| 原版 | 定位、Results、Why/How、六种评分、Example、QC五阶段、Conclusion、唯一参考身份与致谢 | 五幅原始SVG；10页视觉索引对应材料；三个完整题面对照；两模型各八文件全部hunk、十项rubric及各十项结果 |
| 1.1 | 导言、Results、联网问题/方案/替代方案、blocker、Diamond、五条参考身份与致谢 | 6页视觉索引对应材料，另查两初始状态；完整fair-use prompt；14+12步全部panels；原文章节数组 |

原版chart-01/02的PNG相同，1.1的chart-01/02也相同；没有将其算成独立实验。PDF只用来核对页数/映射，科学内容通过原始PNG、SVG文本及展开JSON逐项查看。没有OCR，没有从散点几何拟合未披露数据，没有把截图PDF页码冒充作者论文页码。

两网页无独立技术附录。其引用的METR、Cursor、Datacurve、Posttrain等只核身份和引用角色，没有在本轮扩成全文精读，也没用二手内容填补Cognition未知字段。

## 3. 实际执行的检查

本地Python读取JSON、XML和Markdown；官方JS只静态阅读，没有执行。检查包括：

- 两模型各八文件的逐hunk `add/del` 与元数据一致；Opus总计+53/−11，GPT+69/−22。
- rubric ID与两套results一一对应；前者8/10，后者10/10。只有r1/r2是blocker。
- 两模型三个展示测试文件的对象完全相同；不据此推定真实来源或注入过程。
- 原版93条与1.1的72条聚合，全部满足0≤new_score≤correct≤1；所有字段和null分开记录。
- 1.1所有72条`steps`均为null；原版SWE-1.6的token/cost有null，不替换为0。
- 按每个subset最大score选择effort，复算公开结果表及1.0违规率在1.1最佳effort下的柱值。
- 完整展开fair-use prompt与章节JSON的`collapsible-code`正文逐字相等。
- 14/12步数组全部读取；记录跳号ID和第10个展示步骤的静态flag，不把数组位置当原运行步数。
- 误判图直接核颜色：蓝FP、橙FN。SVG文本顺序先橙后蓝，不按提取顺序映射。
- 独立算术：FP相对下降1−6.9/36≈80.83%；同轴误判份额合计下降1−11/42.8≈74.30%；982/3098≈31.70%；2056/3098≈66.37%；70007.6/15026.7≈4.66。
- 逐页图片链接存在、引用定义、内联导航、数学和代码分隔符、UTF-8及行尾空格检查。

以上不是训练实验、scanner测试、代码编译或对人类真值的重新标注。

## 4. 最重要的事实边界与修订

| 问题 | 检查结果 | 成文处理 |
|---|---|---|
| 81%是否全部误判 | 图例指FP从36.0到6.9；两类份额合计不是81% | 保留导言与另一段宽泛措辞的区别，不改原图 |
| 提示长度是否都为三分之一 | task-only982，完整含guidelines2056，Pro3098 | 两种输入组成分别报告，字符不叫token |
| 演示reward与门控score | fail案例reward=.2357，renderer显示24%；正文规定blocker失败后0 | 列为未解释的展示口径，不擅定是中间分或正式最终分 |
| reverse-classical测谁的测试 | 总述是agent-submitted；案例r9/r10写reference | 保留provenance差异，不合并成同一执行 |
| 网页Run eval是否真执行 | 原版setInterval播放固定files/results；1.1setTimeout播放固定steps/flag | 不称真实模型/测试/scanner复现 |
| 哪一步违规 | prompt禁止精确解法查询；演示第9步精确搜索、第10步打开diff才flag | 不将演示触发点等同完整政策；不假定该轨迹带新版prompt |
| 违规柱图属于哪个版本 | 标题/脚注为1.0，按1.1最佳effort选点 | 不写成prompt后残余违规率，不用它反驳<1%陈述 |
| 75项如何修改 | blocker降级为non-blocker | 不写删除75题/测试，也不声称已测得确切FN降幅 |
| Diamond变化 | 难度排序失效、低通过率噪声，停止报告 | 不推定重建了新Diamond或重新抽Main |
| 同模型分数变化 | 多项协议变化、身份与运行条件不完整 | 不写成模型学习或单一机制因果增益 |
| mutagent确定性 | LLM可改测试或应用代码，然后执行测试 | 不把整条pipeline称为确定性的，也不宣称已验证语义保持 |
| 任务可下载性 | 原版明确暂不公开，1.1没宣布取消 | 不纳入已可自行运行的训练/held-out资产 |

这里既有源文未披露、展示口径与正文差异，也有读者防止误读的说明，不统一称为“论文错误”。

## 5. 可独立复算的核心检查

从仓库根目录运行下面代码，读取已入库来源包；不联网，不执行原始JS或补丁：

```python
import json
from pathlib import Path

root = Path('docs/harness_improve/external_paper_references/reading_notes'
            '/source_supplements/cognition_20260911')

def read(rel):
    return json.loads((root / rel).read_text(encoding='utf-8'))

rubrics = read('frontier-code/embedded/array-576.json')
cases = read('frontier-code/embedded/array-2002.json')
for case in cases:
    assert len(case['files']) == 8
    assert set(case['results']) == {r['id'] for r in rubrics}
    added = deleted = 0
    for file in case['files']:
        rows = [row for h in file['hunks'] for row in h['rows']]
        a = sum(row['kind'] == 'add' for row in rows)
        d = sum(row['kind'] == 'del' for row in rows)
        assert (a, d) == (file['additions'], file['deletions'])
        added += a
        deleted += d
    failed = [r['id'] for r in rubrics
              if r['blocker'] and not case['results'][r['id']]['passed']]
    print(case['id'], added, deleted, failed, case['reward'])

for name, expected in [('frontier-code', 93), ('frontier-code-1.1', 72)]:
    data = read(f'public_data/data/{name}/data.json')
    data = data.get('v1_1', data)
    rows = [v for efforts in data['data'].values()
            for subsets in efforts.values() for v in subsets.values()]
    assert len(rows) == expected
    assert all(0 <= v['new_score'] <= v['correct'] <= 1 for v in rows)
    for model, efforts in data['data'].items():
        effort, point = max(
            ((e, subsets['main']) for e, subsets in efforts.items()),
            key=lambda pair: pair[1]['new_score'])
        print(name, model, effort, point['new_score'],
              point.get('shortcut_rate_1_0'))

stories = read('frontier-code-1.1/embedded/array-2876.json')
assert [len(story['steps']) for story in stories] == [14, 12]
assert [i + 1 for i, step in enumerate(stories[0]['steps'])
        if step.get('flagged')] == [10]
print('FP relative reduction:', 1 - 6.9 / 36)
print('Combined-share reduction:', 1 - (6.9 + 4.1) / (36 + 6.8))
```

这些检查只能确认公开展示数据内部关系，不能代替逐题真值、统计置信度和完整grader复现。

## 6. 剩余边界与后续复查重点

目前没有需要用户重新上传的本任务材料。未公开的完整任务/镜像、原始评分和网络日志、scanner及mutagent源码、人工校准数据、有效样本分母与成本，不因成功解压附件而得到补齐。

独立复查建议优先看：原版fail/24%的数据与renderer；FP/FN图例和81%的对象；reverse-classical的两种测试来源；1.1的旧版违规率/新版effort脚注；精确查询与打开diff两个政策节点。若进一步做工程验证，应以新增最小实验记录其事实，不回写为本轮已经执行。

本轮只提交三个文档。提交前读取最新分支头，使用非强制更新；远程成功与回读结果由最终交付说明给出，本记录不预填尚未发生的commit。共享索引继续由主线程汇总，避免与其他并行线程冲突。
