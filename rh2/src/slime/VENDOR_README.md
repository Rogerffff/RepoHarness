# vendor slime（形态甲冻结兼容包）

本目录是 miles 迁移形态甲（spike-log 2026-08-25 决策）落库的 slime agent 层
vendor 副本：rh2 继续复用 slime 的协议 adapter / TrajectoryManager /
harness / sandbox 代码，训练主链换成 miles 之后不再依赖完整 slime 安装。

- 来源仓库：`THUDM/slime`（本仓库 `reference/slime` checkout）
- 来源 pin：commit `e848052a65092ec49e4dd2b5d44d0787c3a327a4`
  （`[docker] Update dependencies (#2178)`，与 rh2 slime 冻结回退面同 pin）
- 复制日期：2026-08-25
- 复制方式：逐文件 `git show e848052a:<path>`（取 pin blob，**不是**工作树——
  `reference/slime` 工作树对 `slime/agent/adapters/common.py` 有 30 行纯注释的
  本地标注，vendor 不携带）

## 字节级零修补声明

以下 19 个文件与 pin `e848052a` 的对应 blob **逐字节相同**（sha256 已核对）。
截至本文件写入时**没有任何被迫修补**；未来任何修补必须在下方"修补记录"
一节逐条登记（文件、原因、diff 摘要），否则视为违规。

## 文件清单（sha256 = pin blob = 本目录文件）

| sha256 | 文件 |
|---|---|
| e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | `__init__.py` |
| db8ee13dd4891e4b93237ed440d69be2d063986f5bcb20cbe9fcfd6b2ed83a82 | `agent/__init__.py` |
| bb11e40d81542a26b4a4824df683cb6ea9145c74ce8deec328982e34da8f2150 | `agent/adapters/__init__.py` |
| 66ef380a3fc2ee8e582041ac8948857eea5e8a24ff5e9816a51320abedbd8980 | `agent/adapters/anthropic.py` |
| 27bd6c396b6fdd525667df9b33490ab594d38714255073991404daf417d77b11 | `agent/adapters/common.py` |
| e68af264a6ab6436298091a3374d61bc75f128610402c0f5ae201e1a01133af0 | `agent/adapters/openai.py` |
| 651e5aedbf9529d5f2e458bc6fbbd9a1931ec31bc00c9b8c911b6762d1209268 | `agent/aiohttp_threaded.py` |
| 9446446dc967ce4863b959e228917e494f7d2c78f7b452a8eeace4695c9f18e8 | `agent/harness/__init__.py` |
| 94765e59b431da1399cf09fada8693c20971a27e666d8fdb1308b3267b2d2af4 | `agent/harness/claude_code.py` |
| da9f815f777c6268c98203d80afd67d0a079976e7f5f968fba7cc79131f9f1b4 | `agent/harness/codex.py` |
| 57919ecd4240f6631678f4ea395e2e0a784403ed4bb893c5e42992eabbe4b1fa | `agent/harness/common.py` |
| 2c29ed7718fbdbdf88fecd160f528eec22c88e253fc3c3788e271433ffd13b33 | `agent/parsing.py` |
| 3b175938e7f028b6e892608ad2447677693b6b7287bc4943f820aafda63ce193 | `agent/sandbox.py` |
| 6dbb7bec446d81fa0542a4c954d458b4a11edab6776b45a63bc33bca08dd0469 | `agent/trajectory.py` |
| 5043a8723e70046ef3298939bf3f45c11dabfdf15599dcd7519900edf83e332f | `utils/__init__.py` |
| a953708eee259279eda814d4a369fde1cb15f3413159182326efb88a710eeaf5 | `utils/http_utils.py` |
| 667e5fd546ab8e736ee65b94e69ea56dfcdc4fe1c12b5caff0e88d07a4c92982 | `utils/misc.py` |
| 3e52af4c0b69a6fafb1338f0beb225f4c405368cdad970f494c4f58196dcd408 | `utils/types.py` |
| f2429ebb08a024fbd73dd2e7065c9c70b8ba64ef36150014da7b8cfc94e70cb4 | `utils/processing_utils.py` |

## 闭包说明

- 前 18 个文件 = spike P0-1 已验证的 import 闭包（`slime.agent.*` 全部 +
  `slime.utils.{types,misc,http_utils}` + 三级包 `__init__.py`）。重依赖
  （sglang/ray/e2b/megatron）在源码里都是函数内 import，不进闭包。
- `utils/processing_utils.py` 是 R5-ext B8 补上的漏项：
  `rh2/src/repoharness2/adapters/slime/bringup.py:574` 在构造 `BringupService`
  时执行函数内 `from slime.utils.processing_utils import load_tokenizer`。
  该文件自身的 import 闭包只有标准库 + 第三方（`PIL`、`transformers`；
  函数内另有可选的 `qwen_vl_utils` 与 `transformers.models.glm4v`），
  **没有**任何 `slime.*` 内部依赖，因此闭包只新增这一个文件。
  第三方依赖 `pillow` 已加入 rh2 的 dev 依赖组（rh2/pyproject.toml）。
- 有意**不含** `slime/rollout/*`、`slime/ray/*`、`slime/backends/*`、
  `slime/utils/dp_schedule.py` 等训练批次侧模块：形态甲下这些职责由 miles
  承担（spike P0-1 强等价验证中 7 个差异全部落在这一类）。
- `agent/adapters/openai.py`、`agent/harness/codex.py` 按 2026-08-25 用户
  T1 决定暂不裁剪（裁剪会破坏零修补，需改两个 `__init__.py`）。

## 修补记录

（无。任何未来修补逐条追加到这里。）
