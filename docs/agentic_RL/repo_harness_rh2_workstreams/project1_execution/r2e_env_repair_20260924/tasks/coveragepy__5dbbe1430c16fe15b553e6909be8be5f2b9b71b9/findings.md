# coveragepy `5dbbe143`（5.0.2a1）环境审查结论

**结论**：环境无缺口，分类 `env_ok`。处置暂记 `unknown`，只差 R13（中央复跑并入后若一致 → `environment_qualified`）。

**依据**
- R-f：noop 0（仅目标键 `ApiTest.test_warn_once`，TypeError: _warn() got an unexpected keyword argument 'once'）、gold 1（75/75）；对账 agree。
- 探针：十项最小条件满足；python 3.7.9、pytest 4.6.6 + xdist；pip 19.3.1、pip check 无问题；coverage 以 editable finder 安装，/tmp 下也能导入；公开测试 `tests/test_annotate.py` 通过。
- 公开复现：题面示例原样运行即 TypeError（`REPRO_OBSERVED=1`）。
- 脏树只有未跟踪的 install.sh（构建脚本）与 run_tests.sh，无修复痕迹；基线自带 `coverage/__pycache__`（33 个文件，构建时留下，census 剪除、前后不变）。

**缺口**：R13 只有一次运行。

**建议**：无额外解题侧条件（有 pip，但无网络，装不了新包）。

先后说明（E06）：repros 写完后才读 gold 日志。
