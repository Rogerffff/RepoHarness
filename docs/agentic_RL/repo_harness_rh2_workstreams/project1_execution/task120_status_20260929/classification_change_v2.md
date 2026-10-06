# 原第1类38题重新核对

2026-09-29。按用户澄清后的普通探针标准，18题先修复、8题先诊断、12题保留。此次为证据与分类复核，无新运行；原“受限比较”许可、作者probe_ready和S1/S2历史标签均保留，不能自动覆盖本次分类。

统计及当前入口见[总览](README.md)。每项原因只针对声明题目范围；不以全仓全绿或穷尽输入为要求。

## 先修复或验收：18题

| 题目 | 为什么这样分 | 下一步 |
| --- | --- | --- |
| SWE conan-15422 | 已有真实满分候选漏掉公开要求的默认 jobs 与多配置路径，不能再以事后审计豁免。 [依据](../swegym40_status_20260929/reviews/dvc_conan_dask.md) | 补默认 jobs、多配置生成器及所用 CMake/schema 兼容验收；正确修法通过、已存漏修候选被拒后再进普通探针。 |
| SWE dvc-4166 | 目录规则已有明确公开依据，但已验日志存在参数节点合键，文件／目录成对判据也未完整保护。 [依据](../swegym40_status_20260929/reviews/dvc_conan_dask.md) | 固定已验 pathspec/networkx 配方，核当前材料的节点身份；消除合键并补同名文件／目录对照，复验 gold 和只裁尾斜杠的部分修法。 |
| SWE dvc-5839 | CLI 的任意 precision 和默认值是明确要求；现有 F2P 只验实参8，helper 的 P2P 不等于 CLI 值传递已受保护。 [依据](../swegym40_status_20260929/reviews/dvc_conan_dask.md) | 把已跑的默认／4／8 CLI 实际数值断言纳入验收；核 gold、真实成功候选与硬编码8候选。硬编码候选得分仍未实测，不预填。 |
| SWE dvc-6954 | 负数参数公开要求不限于负整数；现有正式目标只覆盖整数，同一通路的负 float 已有可复用行为证据。 [依据](../swegym40_status_20260929/reviews/dvc_conan_dask.md) | 加入已验证的负 float／容器负值及必要 lock 行为验收，复验 gold 和 int-only 候选；保留非法表达式不扩题的决定。 |
| SWE mypy-10174 | 停止误报仍须保留真正不重叠比较的诊断；具体公开负例已定位，但不在冻结参考内。 [依据](../swegym40_status_20260929/reviews/mypy_pydantic.md) | 补同开关下真实不重叠比较的公开负例，验证 gold 保留诊断、关闭全部比较的候选被拒；不把尚未跑的错误候选写成已误奖。 |
| SWE mypy-10424 | 关闭收窄的错误候选已得1且破坏四项公开旧行为，修法已明确。 [依据](../swegym40_status_20260929/reviews/mypy_pydantic.md) | 将现成普通收窄测试接入版本化 P2P，并收口候选安装子命令失败；正确解与已知错解对照通过后进入普通探针。 |
| SWE mypy-15184 | 题面原例在当前 base 不复现，公开替代复现已验证；继续让模型自行发现原例失配不是对该缺陷的处理。 [依据](../swegym40_status_20260929/reviews/mypy_pydantic.md) | 以有公开依据且已验证的同名类例中性修订复现说明，保持限定名目标，补新公开读者及正确／错误行为核对。 |
| SWE mypy-17071 | 禁用 unbound 检查的错误候选已得1，普通未绑定类型必须仍被拒。 [依据](../swegym40_status_20260929/reviews/mypy_pydantic.md) | 把已有真正 unbound 负例接入正式参考，同时核候选安装；成功修法通过、禁用检查候选被拒后再探针。 |
| SWE moto-5960 | 公开核心 GSI KEYS_ONLY 路径缺决定性断言，已有 actor/gold 行为对照，不能只安排成功补丁后检。 [依据](../swegym40_status_20260929/reviews/moto_pandas.md) | 补 INCLUDE／KEYS_ONLY 的字段集合验收，核引用节点身份，运行 gold 与漏修 KEYS_ONLY 候选后再进入普通探针。 |
| SWE moto-6408 | 当前原序列首项正确不证明标签唯一归属及其它标签保留，这属于明确任务要求的覆盖缺口。 [依据](../swegym40_status_20260929/reviews/moto_pandas.md) | 补现有两镜像完整标签集合与对象归属断言，核正确解、只改返回排序和误删其它标签的候选；新目的镜像的邻接旧缺陷另定范围。 |
| SWE pandas-48106 | 三组 Period 修订未处理剩余两组 tz 节点合键；当前都PASS不能消除未来混合状态被覆盖的风险。 [依据](../swegym40_status_20260929/reviews/moto_pandas.md) | 核当前版本两组 tz 引用绑定，补独立身份／混合状态对照并完成版本验收；不将历史0/1追溯改分。 |
| SWE pydantic-8511 | gold 及满分候选的继承 TypeError 已实证，窄修正对照也已可用，既有审计许可不能替代修复。 [依据](../swegym40_status_20260929/reviews/mypy_pydantic.md) | 以已核窄修作正对照，将三类继承保护接入正式验收，收口安装失败并复验；保留原 gold 失败事实。 |
| R2E aiohttp__1c1c0ea3 | C3静默丢失cleanup错误已实证；原例修好不应豁免已经定位的错误保留行为，只登记S2不足以消除此项。 [依据](../r2e_lifecycle_20260929/results/aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52/probe_card.md) | 复用公开旧行为及现成后检，补cleanup错误被抛出或被报告的行为断言，允许gold与C1两条路线、拒绝C3；正式复验后再探针。 |
| R2E aiohttp__61833518 | 示例断言恒真且路径描述不准，真实客户端／服务端又有旧asyncio兼容故障；mock开发通过未修好这些已知路径。 [依据](../r2e_lifecycle_20260929/results/aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2/probe_card.md) | 修订可追溯的公开复现说明，恢复相关客户端／服务端开发兼容或给出并验证等效公开路径；保持压缩/chunked目标与核心修订不变。 |
| R2E coveragepy__ea6906b0 | 生成报告时覆盖用户已有.gitignore是已经定位的破坏性行为，不能以边缘路径登记代替处理。 [依据](../r2e_lifecycle_20260929/results/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/probe_card.md) | 加入已有.gitignore内容保留与忽略效果对照，验证安全合并或其它合理修法；核公开open替身是否误拒encoding写法，一并窄收口。 |
| R2E orange3__4014f248 | 容差合并候选满分却破坏有公开依据的小量级分割，属于已知可修缺陷；还有编译题入口和准备预算待验收。 [依据](../r2e_lifecycle_20260929/results/orange3__4014f2483e3bab0621c9ae0f994947c008183253/probe_card.md) | 纳入已有小量级分割回归控制，核gold及C3，再按最终入口复验build/pyx_only与准备预算；不再仅把C3列为后检。 |
| R2E aiohttp__240da100 | 原例顶层导入及协程调用不能运行，且期望FAILED的兼容死键仍在，不能只等模型偶然翻转再处理。 [依据](../r2e_lifecycle_20260929/results/aiohttp__240da100151933883d7dea0528d45877df025b92/probe_card.md) | 按已核mock等效复现修订公开说明，并核两死键的移除或恢复方案；用已有正确/错误候选及SC1复验，不扩大默认端口/Host等未定范围。 |
| R2E numpy__d805e9b6 | 同一一维打印目标的n>threshold>=1500已有具体静态丢值路线和清楚断言，题面Actual也已证不符；无需等模型撞出才修。 [依据](../r2e_lifecycle_20260929/results/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/probe_card.md) | 补n=3000/threshold=2000的保值摘要对照，核K-A5b与混合截断候选；中性修订Actual说明并复验，不扩题外二维。 |

## 先诊断或核定范围：8题

| 题目 | 为什么这样分 | 下一步 |
| --- | --- | --- |
| SWE dask-8597 | split=True 空轴及默认警告有已定位的部分修复疑点，现有模型成功不能证明评分能排除此类候选。 [依据](../swegym40_status_20260929/reviews/dvc_conan_dask.md) | 运行已设计的 split=True 部分修复与默认警告对照，核正式得分和实际数组；同时确认已验数组开发路径，不能靠候选池身份跳过。 |
| SWE dvc-1681 | 旧 md5 兼容的公开目标与内部 dumpd 断言之间，有尚未消解的合理替代解误拒疑点。 [依据](../swegym40_status_20260929/reviews/dvc_conan_dask.md) | 用固定旧格式样本及真实非默认目录，对照仅在校验输入规范化的解与 gold；决定保留内部断言还是改为外部兼容行为验收。 |
| SWE mypy-16869 | 合法 Unpack 输出是否被逐行字符串验收误拒尚未确定，不能靠后审替代。 [依据](../swegym40_status_20260929/reviews/mypy_pydantic.md) | 构造导入与语义都正确的 Unpack 修法，核 CLI 生成桩及正式六参考，再决定需要修验收还是消除疑点。 |
| SWE pandas-56849 | 同义 warning 的合理候选接受性和参数合键的实际影响仍待辨别，开发重编通过不能消掉它们。 [依据](../swegym40_status_20260929/reviews/moto_pandas.md) | 先验证合理 warning 变体与20期／倍数／freq行为，核逐节点混合状态；确定是修文案验收、引用身份还是保留现规则。 |
| R2E aiohttp__22a12cc2 | 题面直连和非法fingerprint示例与真正代理TLS缺陷不一致；上移校验到connect的合理性也未核，影响解题目标及接受性。 [依据](../r2e_lifecycle_20260929/results/aiohttp__22a12cc2e2ef289d9e96fd87dfc17272177e52ac/probe_card.md) | 先用公开构造契约和CONNECT行为确定中性题面，核上层校验实现是否合理；随后一起完成题面与行为验收修订。 |
| R2E coveragepy__97997d2c | 仅转发并始终给插件Coverage的路线被拒是否有公开依据，原卡仍请求核对且无明确结论。 [依据](../r2e_lifecycle_20260929/results/coveragepy__97997d2cd6801d0335e3fa162b719d6f8c160266/probe_card.md) | 独立核插件公开契约，构造该替代路线并对照配置与combine行为；合理就修验收，否则以依据关闭误拒疑点。 |
| R2E datalad__19f5b450 | stderr的公开依据两边都有，文档会导向评分拒绝的路线；题目预算和HOME git身份也未在目标入口收口。 [依据](../r2e_lifecycle_20260929/results/datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb/probe_card.md) | 先确定允许的退出码／stderr行为并消解文档冲突；随后修公开说明，固定git身份与已验预算，再复验合理与错误候选。 |
| R2E pillow__3a61c9e9 | GIF palette分支mode/字节格式不一致的具体gold风险仍只有源码推断，可能涉及同一调色板要求，不能只写S2放行。 [依据](../r2e_lifecycle_20260929/results/pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07/probe_card.md) | 对GIF palette分支核实际mode、字节及保存读回，区分真实回归与无依据格式扩张；有问题再补有效正对照和验收。 |

## 无需先修已知题级问题：12题

| 题目 | 为什么这样分 | 下一步 |
| --- | --- | --- |
| SWE mypy-10308 | 核心 F2P 已含非题面实例及正负类型行为，缺失 fixture 已修；P2P 为空本身不证明反馈失效，尚无具体未处置误判。 [依据](../swegym40_status_20260929/reviews/mypy_pydantic.md) | 固定 materials_v2 与已验开发入口衔接普通探针；记录未覆盖的其它递归／变型组合，不把缺少全仓覆盖当作当前已知缺陷。 |
| SWE moto-5134 | 核心 null／缺键及实际投递有直接断言；8个成功候选的14种行为与103回归已核，未找到尚未处置的具体误判。 [依据](../swegym40_status_20260929/reviews/moto_pandas.md) | 固定已验 SDK 配方和公开开发条件衔接普通探针；Archive／Replay 等未覆盖接口留作范围说明，出现具体关联问题再回流。 |
| SWE dask-6626 | pytest与runner差异已处理；公开两条路径和非示例dtype对照完成，所测错误候选由原参考正确拒绝，最终独立复核已完成。 [依据](../swegym_cpu_preprobe_20260929/tasks/dask__dask-6626/result.md) | 固定已验 actor/grader 配方和准备预算衔接普通探针；不为已被拒的 object dtype 候选重做评分规则，保留无关依赖及邻接Index范围说明。 |
| R2E numpy__18b7cd9d | None以外的比较及按值相等核心缺口已补并正式验收；剩余list/ndarray等未约定输入不强加新要求，修法提示是难度属性。 [依据](../r2e_lifecycle_20260929/results/numpy__18b7cd9df7a4d960550b18faa14d5473e7d5c3d9/probe_card.md) | 用已验修订版衔接普通探针，报告题面提示程度；不同长度等边界未穷尽不等于已有错误解被允许，出现具体失效再回流。 |
| R2E numpy__5e8301c2 | 核心广播与求和维已有修订及有效C-A正对照；多操作数/路径优化器已明确属本题范围外，原gold缺陷已用替代对照处置。 [依据](../r2e_lifecycle_20260929/results/numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb/probe_card.md) | 固定C-A及修订材料衔接普通探针；保留优化策略等未覆盖范围，不能把未构造的猜测写成已证漏判。 |
| R2E numpy__a5ea773e | 整数及元组reps核心断言已补；已知错误候选均被拒，子类/空reps未约定；无关ctypeslib错误不阻断相关开发。 [依据](../r2e_lifecycle_20260929/results/numpy__a5ea773e66110cf335c9ed37e8ccdc14f8e56764/probe_card.md) | 使用已验相关命令与修订版衔接普通探针；记录其它reps形式，避免为无关公开测试扩题。 |
| R2E pandas__32dd55cb | 核心mean/sum及合理替代解接受性已修；公开旧Period文案冲突已按两种合理文案处置，numeric_only=False的既存限制属于题外范围。 [依据](../r2e_lifecycle_20260929/results/pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0/probe_card.md) | 使用已验修订版衔接普通探针；保留原gold题外局限与公开旧名单式断言说明，允许候选保持或更新合理文案。 |
| R2E pillow__3ac9396e | 核心混合有理数及非示例tag已补；unittest等效开发路径已验，非零分母未登记tag是base已有、已明确不扩的邻接问题。 [依据](../r2e_lifecycle_20260929/results/pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605/probe_card.md) | 沿已验unittest及修订版衔接普通探针；准确说明pytest兼容限制，不强制LONG/SHORT宽度或无依据扩展其它插件。 |
| R2E scrapy__75450e75 | 异步执行与二次fetch已验，K1替代挂起gold后问题已处置；措辞偏差已有公开行为解释，未新增题面矛盾。 [依据](../r2e_lifecycle_20260929/results/scrapy__75450e75d269b2a2b00b6303af1033df1f69cc67/probe_card.md) | 固定K1和已验shell开发入口衔接普通探针；自定义事件循环与无关Twisted旧测作为明确未覆盖范围。 |
| R2E scrapy__9a15fcf8 | 核心MIME别名与死键已修；旧header故障是邻接既有问题，新验收已允许修复它，未发现仍排斥正确目标修法。 [依据](../r2e_lifecycle_20260929/results/scrapy__9a15fcf89a151811de8ac783419df0512c863d5e/probe_card.md) | 用修订版及相关公开命令衔接普通探针；不要求先修全部抓取/header旧故障，也不把这些失败计为候选引入回归。 |
| R2E scrapy__e9387529 | dict/serializer核心缺口已修并使用有效C1；非文本值依公开文档保留，未规定的分支不选边，相关开发已验。 [依据](../r2e_lifecycle_20260929/results/scrapy__e938752973b4fc53e0fa0c0bc68a431613b987e4/probe_card.md) | 固定C1与修订材料衔接普通探针；嵌套非文本键等未约定边界保留中立，不以无关Twisted错误阻断。 |
| R2E numpy__d89bc4bb | 三处核心漏判及浮点误拒已修并正式验收；剩余精确比较经过多种运算顺序检查，尚无具体未处理误拒。 [依据](../r2e_lifecycle_20260929/results/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd/probe_card.md) | 使用已验84键修订版衔接普通探针；density/normed同传等无公开唯一约定的范围保持中立。 |
