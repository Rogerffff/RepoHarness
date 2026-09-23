# 第四批中期根核查

2026-09-21 06:33 SGT。尚未完成主审和独立复核，不是整批验收。根是在收到协调者线索后定点读原件，不宣称独立盲发现；未将此笔记作为未封存reviewer的输入。

**DVC4185的两个公开症状须分开。** 根读了完整题面、gold和test.patch：末尾明确分别报告commit误报未改的get_base_dv，以及status误报false参数。gold仅将fill_values的真值过滤改为键存在判断。新增7个假值用例只直接调用fill_values和dep.status；另一func改动是补上原来缺失的isinstance断言，没有新增commit验收。

根追到原base的`dvc/repo/commit.py:38–48`、`stage/__init__.py:397–410`、完整ParamsDependency及LocalDependency/LocalOutput继承链、`output/base.py:169–195`、`remote/local.py:44`：commit按changed_checksum取changed_entries，参数info保存参数值而继承checksum读md5；不存在覆盖该checksum路径的方法。对非空普通参数文件，这条链支持commit症状未被gold修复的强静态推断。尚未执行CLI；文件存在、参数锁定、安装与代码生效必须由后续对照确认，不把历史gold=1当两个症状都修复。

当前不要求重审已验前三批，不预判本题最终处置。等待fresh主审和独立reviewer自身原件初判，再核其最终结论、历史运行及最小实验。今夜仍未运行项目、测试、容器或模型，也未改原题/评分。
