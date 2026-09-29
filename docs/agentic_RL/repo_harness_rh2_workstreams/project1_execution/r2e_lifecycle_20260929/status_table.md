# 逐题状态（机器汇总，只列事实）

列说明见 `rh2/experiments/r2e_lifecycle_20260929/status_table.py` 文件头；state 以 board.json 为准。

| 题 | state | 复验 noop | 复验 gold | 放宽复验 noop / gold | 修订验收 | devcheck | 准入卡 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| aiohttp__1c1c0ea3 | probe_ready | 0 | 1 | — | v5 6/6/6 | ✓ | probe_ready |
| aiohttp__22a12cc2 | probe_ready | 0 | 1 | — | v5 8/8/8 | ✓ | probe_ready |
| aiohttp__61833518 | probe_ready | 0 | 1 | — | v5 6/6/6 | ✓ | probe_ready |
| coveragepy__5dbbe143 | on_hold | 0 | 1 | — | v5 5/5/5 | ✓ | on_hold |
| coveragepy__97997d2c | probe_ready | 0 | 1 | — | v5 7/7/7 | ✓ | probe_ready |
| coveragepy__ea6906b0 | probe_ready | 0 | 1 | — | v5 6/6/6 | ✓ | probe_ready |
| datalad__19f5b450 | probe_ready | 超时 | 超时 | 0 / 1 | — | — | probe_ready |
| numpy__18b7cd9d | probe_ready | 0 | 1 | — | v4 6/6/6 | ✓ | probe_ready |
| numpy__5e8301c2 | probe_ready | 0 | 1 | — | v4 5/5/5 | ✓ | probe_ready |
| numpy__a5ea773e | probe_ready | 0 | 1 | — | v4 8/8/8 | ✓ | probe_ready |
| orange3__22e98f8f | on_hold | 超时 | 超时 | 0 / 1 | — | — | — |
| orange3__4014f248 | probe_ready | 超时 | 超时 | 0 / 1 | — | — | probe_ready |
| orange3__9b5494e2 | on_hold | 0 | 1 | — | — | — | — |
| pandas__32dd55cb | probe_ready | 0 | 1 | — | — | — | probe_ready |
| pillow__2b061b68 | on_hold | 0 | 1 | — | — | — | — |
| pillow__3a61c9e9 | probe_ready | 0 | 1 | — | v4 8/8/8 | ✓ | probe_ready |
| pillow__3ac9396e | probe_ready | 0 | 1 | — | v5 9/9/9 | ✓ | probe_ready |
| scrapy__75450e75 | probe_ready | 0 | 1 | — | v4 6/6/6 | ✓ | probe_ready |
| scrapy__9a15fcf8 | probe_ready | 0 | 1 | — | v4 5/5/5 | ✓ | probe_ready |
| scrapy__e9387529 | probe_ready | 0 | 1 | — | v4 6/6/6 | ✓ | probe_ready |
| aiohttp__240da100 | probe_ready | 0 | 1 | — | — | ✓ | probe_ready |
| aiohttp__4075c653 | revising | 0 | 1 | — | — | ✓ | — |
| coveragepy__016af5f6 | public_read | 0 | 1 | — | — | — | — |
| coveragepy__f5eb5f21 | on_hold | 0 | 1 | — | — | ✓ | on_hold |
| datalad__16c1ffc3 | on_hold | 超时 | 超时 | 0 / 1 | — | ✓ | — |
| datalad__58ba5165 | public_read | 超时 | 超时 | 0 / 1 | — | — | — |
| datalad__6b6fa389 | investigating | 超时 | 超时 | 0 / 1 | — | ✓ | — |
| datalad__9ba5de09 | queued | 超时 | 超时 | 0 / 1 | — | — | — |
| numpy__2f4a9650 | queued | 0 | 0 | — | — | — | — |
| numpy__43e333e2 | queued | 0 | 1 | — | — | — | — |
| numpy__d805e9b6 | probe_ready | 0 | 1 | — | — | ✓ | probe_ready |
| numpy__d89bc4bb | probe_ready | 0 | 1 | — | — | ✓ | probe_ready |
| orange3__50f6a758 | investigating | 超时 | 超时 | 0 / 1 | — | ✓ | — |
| orange3__c3fb72ba | queued | 超时 | 超时 | 0 / 1 | — | — | — |
| orange3__f237f968 | queued | 0 | 1 | — | — | — | — |
| orange3__f5026689 | queued | 超时 | 超时 | 0 / 1 | — | — | — |
| pandas__19c5eea5 | queued | 0 | 1 | — | — | — | — |
| pandas__294cbc8d | queued | 0 | 1 | — | — | — | — |
| pandas__4ec87eb9 | on_hold | 0 | 1 | — | — | — | on_hold |
| pandas__7dd34ea7 | queued | 0 | 1 | — | — | — | — |
| pandas__87787609 | queued | 0 | 1 | — | — | — | — |
| pandas__f656217a | queued | 0 | 1 | — | — | — | — |
| pillow__2d01f7d0 | revising | 0 | 1 | — | — | — | — |
| pillow__4bc64835 | revising | 0 | 1 | — | — | — | — |
| pillow__a682ceaf | queued | 0 | 1 | — | — | — | — |
| pillow__f9d3ee0f | queued | 0 | 1 | — | — | — | — |
| scrapy__a95a338e | revising | 0 | 1 | — | — | — | — |
| scrapy__cfed9b66 | queued | 0 | 1 | — | — | — | — |

复验（当前材料，缺省预算）：noop 38/48 为 0，gold 37/48 为 1。
board 状态计数：investigating 2，on_hold 7，probe_ready 19，public_read 2，queued 14，revising 4
