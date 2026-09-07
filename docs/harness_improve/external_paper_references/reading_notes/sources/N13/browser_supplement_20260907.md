# N13 浏览器补充读取记录

读取日期：2026-09-07。原文为 OpenAI 官方英文网页。本文是浏览器实际展开后的读数与案例索引，不是独立审计结论，也不是原文完整存档。静态 web 抽取会漏掉交互内容。未保存用户浏览信息。

## N13b

来源：[Separating signal from noise in coding evaluations](https://openai.com/index/separating-signal-from-noise-coding-evaluations/)，2026-07-08。

### 原始图的读数

图题：Share of Dataset Flagged by Issue Type。纵轴：Percent of total dataset。按图例先 Human supervised agent review，再 Human annotations。以下为英文网页渲染文字的一位小数读数；不是根据截图柱高估计。辅助可访问性树将部分值四舍五入到两位小数，不能代替渲染标签。

| 类别 | Human supervised agent review | Human annotations |
| --- | --- | --- |
| Overly strict tests | 14.4% | 17.8% |
| Low-coverage tests | 4.1% | 9.4% |
| Misleading prompt | 6.3% | 7.5% |
| Miscellaneous issues | 1.9% | 1.2% |
| Underspecified prompt | 0.6% | 0.8% |

### 方法图

在浏览器中目视核对 Quality assurance pipeline：model rollouts、patches/diffs、task metadata → automated screening → flagged for review / not flagged；flagged 分成两条审查分支。人类监督 agent 分支先详查、再由 researcher 作最终判断；人工分支每任务五名独立 reviewer。两分支分别输出任务级 broken/not broken 与 category。

原图：[本地 SVG](N13b_quality_assurance.svg)。[官方资产 URL](https://images.ctfassets.net/kftzwdyauwt9/4uTrAMFq4ZJu9wXWZ9gifK/44cf7007c7a81c4bb6214d0cab6a3221/Quality_assurance_pipeline_desktop_light.svg)。下载的是页面公开引用的 light SVG；浏览器目视检查的是同一流程的深色渲染。

### 实际展开的所有案例

| 标签 | 下拉列表/案例 | 原文证据定位 |
| --- | --- | --- |
| Misleading prompt | OpenLibrary-77c16d5；Qutebrowser-e34dfc6 | 前者提示的 Markdown 管道前为一个空格、隐藏断言为两个；后者 SharePoint URL 提示要求不识别为 URL，隐藏 test_is_url 要求识别 |
| Overly strict tests | Navidrome-b65e762（单例） | Broker.SendMessage(ctx, event) 的合法路由实现仍可能因私有 shouldSend 和 senderCtx 名称不同而失败 |
| Underspecified prompt | Flipt-86906cb；Flipt-af7a0be | 前者缓存引用删除问题被身份认证 session/CSRF 测试评分；后者 tracing 兼容迁移被无关缓存弃用警告的两个配置键顺序评分 |
| Low-coverage tests | OpenLibrary-d109cc7（单例） | notes 功能跨数据模型、模板、API、索引、导出；展示的测试只检查 List/Seed 构造 |

两组下拉菜单已展开确认各有两个案例；另两组仅有代码复制按钮，无第二案例选择器。案例正文与代码片段全部阅读；未执行这些仓库测试。

## N13a

来源：[Why SWE-bench Verified no longer measures frontier coding capabilities](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/)，2026-02-23。

在浏览器中读取从导言到 Discussion/Author 的全文，核对六个案例（两类测试缺陷、Django edit_only 线索、三模型污染展示）及所有 prompt/response/gold patch 区块。未见文章专属 PDF、附录或额外方法下载入口。

特别核查：django__django-11451 展示的模型 diff 把新增提前返回放在 UserModel 赋值和 kwargs 回退之前；文章展示的 gold patch 放在 kwargs 回退之后。此处不能称整份 diff 逐字复现，即使函数、条件与两行关键改动一致。此观察来自文章自身两段展示，不是重新运行模型所得。

## 获取限制

直接 urllib 请求两个 openai.com 原文均返回 HTTP 403；web 工具和浏览器可读取。Chrome content.export 不支持，故保留 web 分段抽取文件与本补充记录，不能称完整 HTML 冻结快照。网页无明确修订号或历史内容哈希，本地抓取日期不等于发布版本号。
