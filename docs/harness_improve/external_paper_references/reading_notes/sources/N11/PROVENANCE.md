# N11 来源快照记录

读取日期：2026-09-07（Asia/Singapore）。原始资料由 RadixArk / radixark/miles 提供；原文与作者笔记分开保存。pin 快照是干净本地 reference/miles 对应文件的字节复制；online 文件由官方 `.md` 端点取得，未手动改正文；remote 文件按固定 Git SHA 获取。

| 快照 | 来源 | SHA256 |
| --- | --- | --- |
| [agentic-rollout.online-20260907.md](agentic-rollout.online-20260907.md) | [原始来源](https://miles.radixark.com/docs/user-guide/agentic-rollout.md) | `45e55205999ee5533c1c2b274c9193faf053e262c51f57a72edf889123720c87` |
| [fully-async.online-20260907.md](fully-async.online-20260907.md) | [原始来源](https://miles.radixark.com/docs/user-guide/fully-async.md) | `75a8fd86f19a4ee87f09dd2ec130be59a88bcacb617dd6799ebcf26933e6653a` |
| [agentic-rollout.pin-f2b7c7929.md](agentic-rollout.pin-f2b7c7929.md) | [原始来源](https://github.com/radixark/miles/blob/f2b7c79298a53c53861514d099f7def73bd29f4a/docs/user-guide/agentic-rollout.md) | `d9027abea43782f75facb835d65653c8bbb63ae2bc82e6ab63f49d023c059b8d` |
| [fully-async.pin-f2b7c7929.md](fully-async.pin-f2b7c7929.md) | [原始来源](https://github.com/radixark/miles/blob/f2b7c79298a53c53861514d099f7def73bd29f4a/docs/user-guide/fully-async.md) | `7d12d2063b4946c05d88b4eaf140508569ea49daaa52c0ccc6268ea502fb5c6a` |
| [agentic-rollout.remote-d2fc97ce.md](agentic-rollout.remote-d2fc97ce.md) | [原始来源](https://raw.githubusercontent.com/radixark/miles/d2fc97ce581577e255e494801d7568747d5a10d7/docs/user-guide/agentic-rollout.md) | `638a045980f0b078321fb8a29aad1abb41c58082b970c413eb1222111c8ec7d1` |
| [arguments.remote-d2fc97ce.py](arguments.remote-d2fc97ce.py) | [原始来源](https://raw.githubusercontent.com/radixark/miles/d2fc97ce581577e255e494801d7568747d5a10d7/miles/utils/arguments.py) | `45ce4992566d641f3ab2847b59b475d3ce24905bd3bbebe1306c5c77f10ba30f` |

本地上游 HEAD：`f2b7c79298a53c53861514d099f7def73bd29f4a`；本地集成 HEAD：`98a0272e4158b2c20e3a34d210c79b50159af0f6`；读取时远端 HEAD：`d2fc97ce581577e255e494801d7568747d5a10d7`。远端 HEAD 仅作当日定位，未升级当前集成。

阅读深度：两份 pin/online 文档完整阅读；remote Agentic 对照版本变化；remote arguments.py 只读 session/fully-async pause 与 partial 校验相关段，保存整文件以保留定位语境，并不声称完整审查最新代码。其他 U/I 源码按笔记中 commit + 文件 + 符号定位。主机地址没有进入交付文件。
