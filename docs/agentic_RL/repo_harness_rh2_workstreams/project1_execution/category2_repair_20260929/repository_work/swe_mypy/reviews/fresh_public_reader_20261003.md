# mypy-15184：fresh 公开静态读题

日期：2026-10-03。性质：独立公开读者静态检查；不是运行验收或模型评测。

## 结论

当前公开题面目标清楚，三个复现文件与题面一致，未发现阻碍解题的错误假设。要求是：两个不同类型具有相同短名时，`assert_type` 的失配诊断用限定名区分它们；无歧义名称保持简洁；真实失配继续报错，正确调用继续成功并保留原表达式类型。这些要求与公开 base 的源码、文档和既有测试一致。

题面没有指定文件、函数、补丁或实现步骤。`public_hints` 仅给出工作环境、允许改非测试源码、测试范围等通用操作约束，未给出本题修法。解题者能从公开材料理解预期行为，不需要猜隐藏规则。未读取任何隐藏测试，不能保证未知评分规则与上述公开目标一致。

## 固定输入与 SHA

先读取 `python__mypy-15184/public/review_request.md`，再按其范围读取 manifest、题面、bundle 和三个复现文件。用 SHA-256 及纯数据解析核对，manifest 列出的六项全部匹配；bundle 内 `problem_statement` 的 UTF-8 字节与独立题面完全一致，bundle 的 `base_commit` 与 manifest 一致。

| 公开输入（相对本题 public/） | SHA-256 |
| --- | --- |
| `review_request.md` | `259766b22d6730ed17c0afff54a4e1b0fa58b30eb104b074fc36fe7b9d25a771` |
| `reader_input_manifest.json` | `1595a6c23cdd1de33b5ca5e46493f60bd4cd31d3c683c1c17a3d9ae362672a64` |
| `problem_statement_v1.txt` | `c17659095d0b4ab71caf2fab52dfaa52e9da009212381a7dc46053c015499178` |
| `public_bundle_draft.json` | `129e7341efd8699b2a379262647bb4868c8569429903d745cf5c15d54dba7606` |
| `reproduction/a.py` | `5d430ccf415239ad7acd1e352b2ea5d77e95e65637262a09eecda9fce7fe88cb` |
| `reproduction/b.py` | `5d430ccf415239ad7acd1e352b2ea5d77e95e65637262a09eecda9fce7fe88cb` |
| `reproduction/t.py` | `0128a25c7e154c4acfab60eb781fc74f8152e7b8bdb50cc432b4f83ed89b893e` |

manifest 与 bundle 声明公开 base commit 为 `13f35ad0915e70c2c299e2eb308968c86117132d`。本次只读取指定 base 子树，没有通过 Git 元数据独立验证其提交身份。

## 公开依据

以下路径均相对 `runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15184/base/`。

- 复现定义了 `a.C`、`b.C` 两个独立类，函数 `g(x: a.C) -> None` 有类型注解，内部断言目标为 `b.C`。它描述真实类型失配，要求消除诊断中的同名歧义，而不是使调用成功。
- `mypy/checkexpr.py:3911–3932` 在类型不相同时产生 `assert_type` 失配诊断，并返回 `source_type`。这支持题面的失配与表达式类型边界。
- `mypy/messages.py:1658–1664` 分别格式化来源和目标类型；`2397–2415` 默认使用类短名。静态代码路径支持题面声称的两个 `C` 无法区分，但不是实际运行日志。
- `mypy/messages.py:2584–2602、2638–2661` 的公开类型格式化逻辑已说明：不同类型共享短名时显示 fullname，否则维持简短表示。题面的限定名与简洁要求属于仓库已有诊断惯例；这不是从私有材料获知的规则。
- `docs/source/error_code_list.rst:884–896` 说明推导类型必须匹配 `assert_type` 指定的类型，并以 `typing_extensions.assert_type` 为例。复现导入方式与公开文档一致。
- `test-data/unit/check-expressions.test:931–955` 的 `testAssertType`、`testAssertTypeGeneric` 已覆盖正确调用、`int`/`str` 简短失配诊断、返回类型及泛型语境。`957–989` 另有未注解函数、显式检查未注解函数、union 场景。这些既有测试支持保留原行为；所读片段没有本题跨模块同名类的预期输出，不能声称新问题已被测试覆盖。

题面没有逐项列举泛型等所有组合，也没有规定新的诊断标点格式；其行为目标足够明确，公开格式化惯例可供解题者自行查阅。没有发现必须补写实现提示才能理解的问题。

## 实际范围与未验证项

除固定的七个 public 输入外，仅在上述精确 base 内用文本搜索查看 `mypy/`、`test-data/`、`docs/` 的相关命中，并读取上列源码、测试和文档片段；另外静态读取 `mypy/test/testcheck.py:1–105`（公开类型检查测试入口），搜索 `pytest.ini`（无相关命中）。未访问同批其他目录、private、既有 reviews、gold、hidden、候选修法、其他线程或网络；未安装依赖、SSH、改源码或改题面。

执行过文本读取、SHA 校验和标准库 JSON/字节一致性检查；**没有执行 mypy、复现程序、测试或模型调用**。公开 bundle 声称 `testbed` conda 环境已激活，这仍是未核实的环境说明。镜像可用性、依赖完整性、命令实际诊断、公开测试可收集及通过情况均未知；没有 actor、CPU 或评分通过证据。

本次静态读题无需补充题意。后续运行验收仍需在公开环境执行题面给出的复现命令，并核实：失配持续报错且能区分 `a.C`/`b.C`；无歧义诊断保持简洁；正确调用和表达式类型回归测试通过。运行结果应独立记录，不能用本报告替代。
