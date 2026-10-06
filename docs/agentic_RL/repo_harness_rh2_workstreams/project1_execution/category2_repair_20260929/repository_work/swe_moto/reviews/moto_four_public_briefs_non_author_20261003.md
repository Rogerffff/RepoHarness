# 四题公开开发说明非作者窄核

2026-10-03。审查者：Codex 非作者 subagent。只核 Moto5960／6408／6185／7584 的四份 `public_dev_brief.md` 与原公开材料，以及首次文字修正的差异。没有盲自主求解、模型／SDK／测试／项目执行，没有连接远端，没有读取四题私有评分或补丁。本审查者在此前协作中接触过部分 Moto 私有上下文，**不是公开盲 solver**；本轮实际依据均列在下文。只新增本报告，不修改 brief、原 public、已固定 Moto6114 报告或 probe 请求。

**最终结论：v2 四份说明在本轮范围内无剩余阻断，可作为中性开发环境说明交付。** 原 hints 逐字保留，base／workdir 对应正确，功能要求仍由原 issue 定义；新增文字不含私有断言、对照、修法或答案，没有宣称 CPU 已验。原 v1 的绝对解释器路径缺少四题公开／实际证据支持，已通过小范围文字修正关闭；当前使用原 hints 中 testbed 环境的 `python`，实际激活、解释器、导入、安装和测试仍待各题既定 CPU 验收。本结论不提供四题 CPU 准入、fresh actor、probe 或训练资格，也不要求为这次静态文字核查运行测试。

## 输入身份与实际读取

最终入口为 [moto_four_public_briefs_inputs_v2_20261003.json](moto_four_public_briefs_inputs_v2_20261003.json)，SHA `1fc069d44f02cf5530b2df8d75a0fc6120ed11dcc171003ba4ef1a59251201d8`，与交接一致。原入口 SHA `cc96b2bf100ff472b31a0caaab240f63261353fcccd11944e9f665bf47540f2c`。四份 source_public 的路径／SHA／长度在 v1→v2 之间未变；最终 **8 件** public bundle 与 brief 的 SHA／字节数全部独立重算匹配，未直接接受入口里的 `functional_statement_changed=false` 或 scope 结论。

逐题读取了入口指定的完整 public bundle、最终 brief 和保留的 v1 brief，以及同一 public 目录的 `base_identity.json`、`environment_brief.md`、公开 base 的 `Makefile`、`Dockerfile` 和 `docs/docs/getting_started.rst` 中测试凭据段。只用标准库文件／JSON／哈希／差异读回，并在四个公开 base 内检索绝对解释器路径和可选环境变量，没有执行其中代码。public 目录来源为：5960／6408／6185 在 `runs/swegym_quality_batch03_20260921_v1/public/<instance_id>/`，7584 在 `runs/swegym_quality_batch02_20260921_v1/public/<instance_id>/`。

| 题目 | 原 public SHA／字节数 | 最终 brief SHA／字节数 |
| --- | --- | --- |
| Moto5960 | `1cceadd574085e3ecb355ae2346fd56e6e35c57a526d520ae95a41ce55167654`／6,599 | `86e66282608e8e0dfb49ac79f687b9bdbbf0552fb9c27044b67954fb198a7d94`／1,534 |
| Moto6408 | `d195f0b824555d8340301d17fa9c145e1bc82d3033a1399220e115ba87326fc2`／3,027 | `165eb1244f56dbba8403ee032268b29bd43a91c3e87b1554a582e9e54ccfbcca`／1,534 |
| Moto6185 | `805cce4840d0c1625c699445a037bc828a9287d0a4a1775aa1a33520a4c14c5a`／3,809 | `da997fc645f47c08dc4d0b859608ca128f6ebcd6c922cdebe8cdf6403f7e4349`／1,534 |
| Moto7584 | `3f8e76968c45fcd16bd3ffe132ab7ee891c645cfbc8467b16b2d2ea32ba7d586`／2,771 | `cd0915ff5ed8aecb44550320251d66bc1bffe41e254bb8f332396bccf74c464c`／1,534 |

## 逐题对应与功能边界

四份 brief 在“以下为原公开任务的开发说明，内容保留”之后，精确等于对应 `public_hints` 加一个文件终止换行；hints 内容本身未改、只出现一次。四份均保留 `/testbed`，base 同时与 public bundle 和公开 base_identity 对应。原 problem_statement 的 UTF-8 SHA 逐题重算与原字段相等；brief 没有重新解释功能要求或加入替代 statement。

| 题目 | 精确 base | 原公开功能范围（仅作对应说明） | statement SHA |
| --- | --- | --- | --- |
| Moto5960 | `d1e3f50756fdaaea498e8e47d5dcd56686e6ecdf` | DynamoDB GSI scan 的 INCLUDE／KEYS_ONLY 投影。brief 未添加属性集合、反例或修复位置。 | `09e9327d2109afd7563f89bab3aa4da453332574e66bfcdd36f0996c852066c9` |
| Moto6408 | `1dfbeed5a72a4bd57361e44441d0d06af6a2e58a` | ECR 多 tag 图片场景中已有 tag 的移动回归。brief 未添加 digest／tag 新断言、对照或修法。 | `194d518ddb637ce2931cc689e55d39f971c60854bcaccf77f94bd02f7a20ee2d` |
| Moto6185 | `dc460a325839bc6797084a54afc297a2c9d87e63` | DynamoDB Item 中键名 S（包括嵌套）导致 SerializationException。brief 未添加负载、SDK 固定版本、私有用例或答案。 | `9b62e5cdc7ba69076e71c00bdb2b57abbc45cab1779b9a1990b4741c277d0e98` |
| Moto7584 | `cc1193076090f9daf90970db286b6b41581dd8bc` | SNS application 协议对不存在 endpoint 的 subscribe 应报错。brief 未添加错误文本匹配、用例、对照或修法。 | `572c500f4f1fc31bbab5e77e309e6cc046446932ecdad9eb0b92dec14aa894bc` |

删去题号和 base 差异后，四份最终 brief 的其余文字逐字相同。新增内容只是工作区与环境使用说明及环境核对命令；该命令打印解释器、导入路径和 SDK／pytest 版本，没有执行题目功能、断言或私有评分。原 hints 中的测试编辑限制及评分解释是保留的公开指令，本轮核的是保存关系，不把旧文字当成当前机制已实测的证明，也没有自行改写其契约。

## 通用环境说明的公开依据

**解释器与本地导入。** 原 hints 已写明 testbed conda 环境和该环境的 `python`／`pip`／测试工具；v2 沿该公开约定使用 `python`，并以 `sys.executable`／`moto.__file__` 打印实际情况。要求 Moto 从工作区源码导入符合源码修复任务及公开 Makefile 的 editable install 入口，不指定私有补丁或修复模块。原公开 `environment_brief.md` 明确这些材料不是实际容器记录，解释器激活、依赖和相关测试需另做 CPU 验证。本报告保留该边界，未把原 hints 的“已激活”当成四题运行证明。

**原安装入口。** 四个公开 base 的 Makefile 均有 `init` 目标，内容均为 `pip install -e .` 后接 `pip install -r requirements-dev.txt`；所以新增 `make init` 有逐题公开源码依据。它表示项目安装入口存在，不能推成离线依赖已齐、安装实际成功或全仓测试可执行。

| 题目 | Makefile 行 | Makefile SHA |
| --- | --- | --- |
| Moto5960 | 17–19 | `9b98ce0154b671af5864ecd69a910683631085028d721963ed6df4a2b4922970` |
| Moto6408 | 17–19 | `47ddd9f1bb7149e2fae9ea1b273516af8490e5f1f931751104c825f55fe2b8bc` |
| Moto6185 | 17–19 | `6a91d45d9be5d2b15d04c2a48fe2bab6ebc4208e4bb4947a2b4688e47971975c` |
| Moto7584 | 16–18 | `ea0bbd51fa13cf027714c91e5633c4275a060355cbad82c3599fa6a2eb4cc377` |

**模拟凭据。** 四个公开 base 的 `docs/docs/getting_started.rst` 分别在 5960／6185 的 210–218 行、6408 的 216–224 行、7584 的 215–223 行明确说明 dummy 环境变量并给出 `AWS_ACCESS_KEY_ID='testing'`、`AWS_SECRET_ACCESS_KEY='testing'`。brief 的模拟 AWS 凭据说明有此公开依据，不要求真实账户。`AWS_EC2_METADATA_DISABLED=true` 是新增的可选通用 SDK 环境设置，未伪称原 hints 或原 Moto 文档逐字包含此项，也没有任务特定功能、SDK 版本或评分断言。本轮未运行 SDK，不能将设置可用性写成已验结果。

## v1 发现、最小修正与最终边界

初版新增句子及检查命令写死 `/opt/miniconda3/envs/testbed/bin/python`。给定四个 public bundle 只提供 testbed 环境名，公开环境说明明确运行条件未验；已读 base Dockerfile 是 Moto server 构建入口（python slim、/moto），不是这些 SWE 镜像的实际 inspect 或激活记录。四个公开 base 内也未找到该绝对路径。**因此初版的绝对路径没有得到四题公开来源或跨题实际证据支持；不能由 Moto6114 的运行成功推成四题镜像事实。** 这是证据与文字精度问题，不是私有答案泄漏，也不表示四题不可运行。

题主已作最小修正。本轮逐题比较保存的 v1 与 v2，差异只有两处：

1. 新增环境句子改为沿原公开说明使用 testbed 环境的 `python`，并将“可以核对环境”改为“可以核对实际解释器与导入”。
2. 命令改用 `python -B -c ...`，其 imports／打印字段、其余说明、base、workdir 和原 hints 均不变。

最终四份文件不再含 `/opt/miniconda3`。原 v1 四件保留在 `runs/category2_repair_20260929/moto_cpu_20261003/four_public_briefs_initial_v1/<instance_id>.md`，其 SHA 分别与原入口 5960／6408／6185／7584 的 `186e2f0f0f1b89ab39a3896ce0bb95ca14d5ba045c58456090c160db9c77e504`／`cefd4c4be2a8085ce52972ad0b97a2f27f0193dddae31bf2fa7aa5ccbaf00948`／`f95d84a4735b0b6f5c692556c53bb007d79312537a73c3b9b106582feac96de9`／`91512c0e21a965779d687b4a978d7b9508d7c72e1be2c4d63feba4a89deff43f` 精确相等；没有静默覆盖最初的审查输入。

该修正已关闭本轮唯一具体文字问题。四题仍未正式 CPU 验收，brief 也未写 CPU／actor 已通过；原 hints、公共功能 statement 和原 bundle 未改变。本报告不验证最终模型消息是否包含 brief、不验证命令实际执行、不跨题复用运行结论、不增加盲自主求解或测试要求；后续按各题原定流程核实际身份、激活、导入及安装条件即可。
