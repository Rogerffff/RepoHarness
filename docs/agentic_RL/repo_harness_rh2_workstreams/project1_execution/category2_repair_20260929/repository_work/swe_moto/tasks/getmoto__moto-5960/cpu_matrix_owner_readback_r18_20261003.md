# Moto5960：R18 三臂实际评分读回

2026-10-03。新R18三臂实际raw **0／1／0**；每臂原make init完整退出0。整题仍待公开actor开发与非作者结果验收，当前未授予普通探针或训练资格。

| 控制 | job | 安装rc／秒 | pytest rc／秒 | 参考实际状态 |
| --- | --- | --- | --- | --- |
| noop | moto5960-cpu-eeaa3dd27a5d | 0／10.346 | 1／28.048 | 原3F失败，155P通过 |
| gold | moto5960-cpu-66515b832d45 | 0／10.793 | 0／26.479 | 全部159实际项通过，158 parser参考通过 |
| omit_keys_only | moto5960-cpu-66515b832d45 | 0／9.892 | 1／26.292 | 新GSI scan KEYS_ONLY精确失败；其它F/P通过 |

两job的runtime_inputs逐字节相等，固定release、consumer、材料、ENV、三wheel COPY供应、脚本和预算一致，因此组成同条件三臂，不重复noop。每臂实际159项、parser158唯一key；两个历史空格参数都PASSED并合一个key，无缺失、跳过或未知参考，未改parser。

omit完整失败trace在4754行：扫描两行Items仍包含payload alpha／beta，实际集合与期望仅id、gsi_id不同；Count/Items数量断言已通过。该反例准确漏KEYS_ONLY，非环境失败；本次R18原评分0不改写旧R5未知得分，也不把材料定义的constructed_negative_unrun字样当当前运行事实。

两个job外层父退出和三次CLI wrapper均0。逐臂trusted restore/setup完整，原材料和脚本身份相符。CLI footer rows1、halted/aborted空、candidate/manager关闭无残留，每臂自有标签容器/网络两查询均0且空；逐参考作者检查均true。首次noop45件、后两臂60件全部SHA/bytes核过；后两臂归档 `680fc0692dcb4daab251c223eee6e6d3f38b5badf480db73146e7b72ad390cd8`，manifest `34d5839117a5a00ceb957c7a93836b60baadec80c8448ecc73596133c6d8aa8c`。原件根为 `runs/category2_repair_20260929/moto_cpu_20261003/<job>_evidence/`，逐参考读回同级 `<job>_author_raw_readback_r18_v1.json`。

旧R13安装2及结果完整保留，不作为新环境成功。UID54321原公开make init补查已经派发 `moto5960-uid-a680fa8321a6`，尚不算闭合或真实CC。随后完成真实CC公开命令和非作者审查。
