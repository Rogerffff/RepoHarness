# coveragepy `f5eb5f21`（5.0.5a0）环境审查结论

**结论**：环境无缺口，分类 `env_ok`。处置暂记 `unknown`，只差 R13。

**依据**
- R-f：noop 0（仅目标键 `JsonReportTest.test_branch_coverage`，totals 缺 covered_branches / missing_branches）、gold 1（4/4）；与 M3 + 09-09 共 5 份参考日志对账 agree。
- 探针：十项最小条件满足；python 3.7.9、pytest 4.6.6 + xdist；pip 20.0.2、pip check 无问题；coverage 可在 /tmp 下导入；公开测试 `tests/test_annotate.py` 通过。
- 公开复现：最小等价调用（branch=True 测带分支的小模块再出 JSON 报告）totals 缺这两个键（`REPRO_OBSERVED=1`）。
- 脏树只有未跟踪的 install.sh 与 run_tests.sh，无修复痕迹。

**缺口**：R13 只有一次运行；期望只有 4 键，判分面较窄（题目质量问题，不属本轮）。

**建议**：无额外解题侧条件。

先后说明（E06）：repros 写完后才读 gold 日志。
