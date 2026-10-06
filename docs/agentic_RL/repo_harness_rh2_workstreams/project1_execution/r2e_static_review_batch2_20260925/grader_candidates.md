# R2E 第二批：主审与复核提出的候选，真实评分结果（2026-09-25）

Claude（B 线 R2E 协调者）执行。做法与[首批](../r2e_static_review_20260925/grader_candidates.md)相同：用与正式评分同一套 RH2 回放代码，在当前派生镜像上给候选评分，每个候选跑 1 次。**本页只记运行事实**，处置以各题 `card.md` 与 `review.md` 为准。

补丁由协调者按题卡里"可直接改成补丁的描述"写成，都只改库源码，不碰测试或 conftest（账本 `candidate_touched_conftest_or_fixture` 均为空）。每个补丁都在 v3 公开工作树的基础上改写，用 `git diff` 导出。

- **机器**：A 线借给 B 线的 CPU 机（x86_64）。
- **材料与镜像**：`prepared_c`（v3 材料）与 `derived9`（本批 12 题各一张派生镜像，配方 `r2e_derive_v1`）。每题先跑 gold 对照，都得 1。
- **证据**：本机 `runs/r2e_actor_20260925/grader/`：
  - `ledger_<标签>.jsonl`：账本；`eval_logs/`：评分日志；
  - 补丁在 `runs/r2e_actor_20260925/grader_cands/`；
  - `postcheck_b2/`：语义复核（不计入 reward）；`private_regrade/`：构建后私有比对（不计入 reward）；`numpy5e83_extra/`：numpy 手动命令。
- **复核脚本**（都在 `rh2/experiments/r2e_actor_20260925/`，未跟踪，不交给求解者）：
  - `postcheck/run_postcheck.py`：一次性容器（root、不联网）应用候选后跑对应的语义检查；
  - `postcheck/private_regrade_build.py`：应用候选、可选先构建，再像评分那样放入隐藏测试并逐键比对；
  - `private_control_full.py`：私有 gold 对照的全量输出版（首批用的版本只留 800 字符尾部）。

## 1. 正式评分

| 题 | 候选（补丁） | 预期（来源） | 实测 reward（期望键匹配） | 不符的键 |
| --- | --- | --- | --- | --- |
| numpy `5e8301c2` | gold | 1 | 1（35/35） | — |
| 同上 | C-C：base 上把 `einsum_path` 的 `if dimension_dict[char] != dim:` 改成 `... and dim != 1:`，不更新字典（`numpy_5e83_CC_relax_one_direction.patch`） | 1（主审：蒙混） | **1**（35/35） | — |
| 同上 | C-A：gold，再在 `einsum()` 收缩循环里，若 `blas` 为真且 `idx_rm` 中有维度两侧长度不同，就令 `blas = False`（`numpy_5e83_CA_gold_plus_blas_guard.patch`） | 1（主审：更完整） | 1（35/35） | — |
| coveragepy `97997d2c` | gold | 1 | 1（44/44） | — |
| 同上 | W1：只改 `coverage/control.py`，`Coverage.get_option` / `set_option` 开头特判 `"paths"`，读写 `self.config.paths`（`coveragepy_9799_W1_control_layer_only.patch`） | 1（主审：部分实现） | **1**（44/44） | — |
| 同上 | W2：只改 `coverage/config.py`，`set_option("paths")` 存到旁路属性 `_paths_override`，`get_option("paths")` 读它（`coveragepy_9799_W2_side_attribute.patch`） | 1（主审：旁路存储） | **1**（44/44） | — |
| 同上 | A1：只改 `coverage/config.py`，`set_option("paths")` 复制成 `OrderedDict` 并对每个路径 `expanduser` 后赋给 `self.paths`；`get_option` 返回副本（`coveragepy_9799_A1_copy_and_expand.patch`） | 1（主审：合理替代） | 1（44/44） | — |
| 同上 | M：gold，但 set 分支改成 `self.paths.update(value); return`（合并而非替换；`coveragepy_9799_M_merge_paths.patch`） | 1（复核者：替换与合并测不出区别） | **1**（44/44） | — |
| 同上 | N1：只在 `CONFIG_FILE_OPTIONS` 末尾加 `('paths', 'paths')`（`coveragepy_9799_N1_config_file_option.patch`） | 0（主审：负对照） | 0（16/44） | 28 个键 FAILED（日志：读任何配置文件都报 `not enough values to unpack (expected 2, got 1)`，即新条目的 `'paths'` 没有 `section:option` 形式） |
| orange3 `4014f248` | gold | 1 | 1（27/27） | — |
| 同上 | C2：只改 `Orange/preprocess/_discretize.pyx` 的 `split_eq_freq`，两处 `return` 改成 `sorted(set(...))`，不改 `.py`（`orange3_4014_C2_pyx_only.patch`） | 0（主审：交付层误拒） | **0**（26/27） | `TestEqualFreq.test_below_precision`（与 noop 相同） |
| 同上 | C3：`EqualFreq.__call__` 非 SQL 分支在 `split_eq_freq` 之后 `points = sorted(set(round(float(p), 10) for p in points))`（`orange3_4014_C3_round_dedupe.patch`） | 1（主审） | 1（27/27） | — |
| 同上 | C1：`Discretizer.create_discretized_var` 里 `lpoints = list(points)` 之前加 `points = sorted(set(points))`（`orange3_4014_C1_dedupe_in_create_var.patch`） | 1（主审） | 1（27/27） | — |
| 同上 | C4：只在 `self.n >= d.shape[1]` 时 `points = list(np.unique(points))`（`orange3_4014_C4_unique_only_when_n_ge_len.patch`） | 0（主审） | 0（26/27） | `TestEqualFreq.test_below_precision` |
| aiohttp `1c1c0ea3` | gold | 1 | 1（56/56） | — |
| 同上 | C1：`run_app` 的 `finally:` 里 `_cancel_tasks({main_task}, loop)` 改成 `if not main_task.done(): ...`（`aiohttp_1c1c_C1_skip_done_main_task.patch`） | 1（主审：合理替代） | 1（56/56） | — |
| 同上 | C3：换成 `main_task.cancel()` 加 `loop.run_until_complete(asyncio.gather(main_task, return_exceptions=True))`（`aiohttp_1c1c_C3_gather_swallow.patch`） | 1（主审：可能蒙混） | **1**（56/56） | — |
| 同上 | C5：删掉 `_cancel_tasks({main_task}, loop)` 一行（`aiohttp_1c1c_C5_drop_main_cancel.patch`） | 0（主审：常见错误） | 0（49/56） | TestShutdown 的 7 个键（`test_shutdown_close_websockets`、`test_shutdown_handler_cancellation_suppressed`、`test_shutdown_new_conn_rejected`、`test_shutdown_pending_handler_responds`、`test_shutdown_timeout_handler`、`test_shutdown_timeout_not_reached`、`test_shutdown_wait_for_handler`） |
| 同上 | gold，同一台机上并行 6 次（复核者提的时序键实验） | 1 | 6 次都是 1（56/56）；`test_shutdown_handler_cancellation_suppressed` 6 次都 PASSED | — |
| numpy `a5ea773e` | noop | 0 | 0（31/32） | `TestTile.test_tile_one_repetition_on_array_gh4679` |
| 同上 | gold | 1 | 1（32/32） | — |
| 同上 | A：`tile` 里 `c = _nx.array(A, copy=False, ...)` 改成 `copy=True`，无条件复制（`numpy_a5ea_A_always_copy.patch`） | 1（主审：合理替代） | 1（32/32） | — |
| 同上 | B：函数开头 `if isinstance(reps, int) and reps == 1: return _nx.array(A, copy=True, subok=True)`（`numpy_a5ea_B_scalar_one_only.patch`） | 1（主审：部分修复） | **1**（32/32） | — |
| 同上 | C：`d = len(tup)` 之后，全 1 且 `A` 是 ndarray 时 `return A.copy()`（`numpy_a5ea_C_all_ones_return_copy.patch`） | 1（主审：回归型错误） | **1**（32/32） | — |
| 同上 | 复核者 C2：`copy=(tup == (1,))`（`numpy_a5ea_RC2_copy_if_tup_is_1.patch`） | 1（复核者：只修标量 1） | **1**（32/32） | — |
| 同上 | 复核者 C3：全 1 时 `return _nx.array(A, copy=True, subok=True)`，不传 `ndmin`（`numpy_a5ea_RC3_early_return_no_ndmin.patch`） | 1（复核者：丢掉维度提升） | **1**（32/32） | — |
| 同上 | D：末行改成 `r = c.reshape(shape); return r.copy() if r is A else r`（`numpy_a5ea_D_identity_check_negative.patch`） | 0（主审：负对照） | 0（31/32） | `TestTile.test_tile_one_repetition_on_array_gh4679` |
| datalad `19f5b450` | gold | 1 | 1（19/19） | — |
| 同上 | K1：`_run_with_exception_handler` 的 `IncompleteResultsError` 分支里，取第一条 `action == 'run'`、`exception` 是非零 `CommandError` 的记录，先 `_communicate_commanderror(e)` 再 `exit_code = e.code`（`datalad_19f5_K1_communicate_first_run_error.patch`） | 1（主审：正对照） | 1（19/19） | — |
| 同上 | K2：只改 `core/local/run.py::_execute_command`，删掉 `try/except CommandError`，让异常直接上抛（`datalad_19f5_K2_propagate_command_error.patch`） | 1（主审：沿用冲突 docstring 的回归实现） | **1**（19/19） | — |
| 同上 | K3：分支里只加 `exit_code = exc.failed[0].get('exit_code')`，缺字段不回退（`datalad_19f5_K3_first_failed_exit_code_no_fallback.patch`） | 1（主审：部分实现） | **1**（19/19） | — |
| 同上 | H：分支里只加 `exit_code = 3`，硬编码题面给的值（`datalad_19f5_H_hardcode_exit_3.patch`） | 1（复核者：硬编码） | **1**（19/19） | — |
| 同上 | K4：gold，再在 `exit_code = non0_codes[0]` 之后向 `sys.stderr` 打印一行（`datalad_19f5_K4_gold_plus_stderr_print.patch`） | 0（主审：负对照，检验 stderr 约束） | 0（18/19） | `test_run_exit_code`（`assert 'datalad: com...with code 3\n' == ''`） |
| pillow `3ac9396e` | noop | 0 | 0（10/11） | `TestFileTiffMetadata.test_exif_div_zero`（期望 PASSED，实际 ERROR） |
| 同上 | gold | 1 | 1（11/11） | — |
| pillow `3a61c9e9` | noop | 0 | 0（70/71） | `TestImage.test_remap_palette` |
| 同上 | gold | 1 | 1（71/71） | — |
| 同上 | C1：按 `getpalettemode()` 定步长取项，C 层写 RGB 再 `putpalettealphas` 补 alpha（`pillow_3a61_C1_rgb_plus_alphas.patch`） | 1（主审：合理替代） | 1（71/71） | — |
| 同上 | W1：gold，但把模式判定移到 `if source_palette is None:` 之前，显式传入的 `source_palette` 也按图自身模式的步长读（`pillow_3a61_W1_mode_for_explicit_source.patch`） | 1（主审：较自然的错误实现） | **1**（71/71） | — |
| 同上 | W2：gold，但写回 C 层时只写 RGB（`pillow_3a61_W2_python_layer_only.patch`） | 1（主审：只修 Python 层） | **1**（71/71） | — |
| 同上 | W3：base 上对"P 模式、不传 source、恒等映射"直接 `return self.copy()`（`pillow_3a61_W3_identity_shortcut.patch`） | 1（主审：硬编码） | **1**（71/71） | — |
| 同上 | W5：base 上在 P 分支 `self.load()` 之后就地 `self.putpalette(self.getpalette("RGB"))`，把调用者的原图改成 RGB，再走 base（`pillow_3a61_W5_mutate_source_to_rgb.patch`） | 1（复核者：断言在调用之后才读原图） | **1**（71/71） | — |
| scrapy `e9387529` | noop | 0 | 0（61/62） | `PythonItemExporterTest.test_export_binary` |
| scrapy `e9387529` | gold | 1 | 1（62/62） | — |
| 同上 | C1：`PythonItemExporter.export_item` 在 binary 时把顶层键 `to_bytes`，`_serialize_dict` 不动（`scrapy_e938_C1_bytes_keys_when_binary.patch`） | 1（主审：合理替代） | 1（62/62） | — |
| 同上 | C2：只在 `self.binary and isinstance(item, BaseItem)` 时把顶层键转 bytes（`scrapy_e938_C2_items_only.patch`） | 1（主审：不完整） | **1**（62/62） | — |
| 同上 | 复核者 C2：`_serialize_dict` 里 binary 时 `key = to_bytes(key, self.encoding)`，`export_item` 同 C1（`scrapy_e938_RC2_keys_everywhere.patch`） | 1（复核者：合理替代） | 1（62/62） | — |
| 同上 | C3：不看 `self.binary`，总把顶层键转 bytes（`scrapy_e938_C3_always_bytes_keys.patch`） | 0（主审：错误实现） | 0（59/62） | `PythonItemExporterTest.test_nested_item`、`test_export_list`、`test_export_item_dict_list` |
| coveragepy `ea6906b0` | noop | 0 | 0（40/46） | `HtmlDeltaTest` 的 6 个键（`test_html_created`、`test_html_delta_from_coverage_change`、`…_coverage_version_change`、`…_settings_change`、`…_source_change`、`test_status_format_change`） |
| coveragepy `ea6906b0` | gold | 1 | 1（46/46） | — |
| 同上 | C-A：base 上在 `report()` 开头记下目录原本是否为空，报告写完后只在原本为空时写 `.gitignore`（内容 `*`）（`coveragepy_ea69_CA_only_if_dir_was_empty.patch`） | 1（主审：合理替代） | 1（46/46） | — |
| 同上 | C-B：`make_local_static_report_files()` 里只写一个空的 `.gitignore`（`coveragepy_ea69_CB_empty_gitignore.patch`） | 1（主审：错误实现，检验宽松判定） | **1**（46/46） | — |
| 同上 | C-C：gold，但 `open(..., "w", encoding="utf-8")`（`coveragepy_ea69_CC_gold_with_encoding.patch`） | 0（主审：公开约束对照） | 0（39/46） | `HtmlDeltaTest` 的 7 个键，日志 `TypeError: open() got an unexpected keyword argument 'encoding'`（测试用 `mock.patch("coverage.html.open", ...)` 换成只收 `filename, mode` 的假 `open`，公开 `tests/test_html.py:104,136` 同样如此） |
| 同上 | 复核者：`report()` 开头 `ensure_dir(self.directory)` 后立即写 `.gitignore`（内容 `*`），再读数据（`coveragepy_ea69_RE_gitignore_before_data_check.patch`） | 1（复核者：破坏"无数据不建目录"） | **1**（46/46） | — |
| aiohttp `22a12cc2` | gold | 1 | 1（18/18） | — |
| 同上 | K1：`_create_proxy_connection` 里拿到 `start_tls` 后的 transport，再经 `self._get_fingerprint(req)` 校验（`aiohttp_22a1_K1_check_tls_transport_in_proxy_path.patch`） | 1（主审：合理替代） | 1（18/18） | — |
| 同上 | K2：位置同 gold，但指纹直接取 `req.ssl` / `self._ssl` 里的 `Fingerprint`，不经 `_get_fingerprint`（`aiohttp_22a1_K2_fingerprint_without_helper.patch`） | 0（主审：语义等价但与 mock 耦合） | **0**（17/18） | `TestProxy.test_https_connect_fingerprint_mismatch`（期望 PASSED，实际 FAILED） |
| 同上 | K3：在 `_create_proxy_connection` 里校验连到代理的原始 TCP transport（`aiohttp_22a1_K3_check_raw_proxy_transport.patch`） | 1（主审：错误修复） | **1**（18/18） | — |
| 同上 | K4：`start_tls` 之后只要配置了指纹就一律抛 `ServerFingerprintMismatch`（`aiohttp_22a1_K4_reject_any_fingerprint.patch`） | 1（主审：过度拒绝） | **1**（18/18） | — |
| 同上 | 复核者 C：gold，但不匹配时改用 `tls_transport.abort()`（`aiohttp_22a1_RC_gold_but_abort.patch`） | 0（复核者：合理但会被误拒） | **0**（17/18） | 同一目标键；日志 `NotImplementedError`（`asyncio/transports.py:145`，测试替身 `TransportMock` 没实现 `abort`） |
| scrapy `75450e75` | gold | 1 | 1（17/17） | — |
| 同上 | K1：`commands/shell.py` 的 `_start_crawler_thread` 里，asyncio reactor 下先 `asyncio.set_event_loop(reactor._asyncioEventloop)` 再启动（`scrapy_7545_K1_reuse_reactor_loop.patch`） | 1（主审：合理替代） | 1（17/17） | — |
| 同上 | K1b：`utils/defer.py` 的 `deferred_from_coro` 与 `deferred_to_future` 都先 `asyncio.get_running_loop()`，失败再退回（`scrapy_7545_K1b_running_loop_both.patch`） | 1（主审：另一族合理解） | 1（17/17） | — |
| 同上 | K2：只按 K1b 改 `deferred_from_coro`，重复 5 次（`scrapy_7545_K2_running_loop_from_coro_only.patch`） | 0（主审：不完整） | 5 次都是 0（16/17） | 每次都是 `ShellTest.test_shell_fetch_async` |
| 同上 | K3：取循环失败时退回 `ensureDeferred(o)`，`maybe_deferred_to_future` 吞掉 `RuntimeError`（`scrapy_7545_K3_mask_runtimeerror.patch`） | 1（主审：掩盖根因） | **1**（17/17） | — |
| pillow `3ac9396e` | K1：`ImageFileDirectory_v2._setitem` 里，未注册 tag 且值全是 `IFDRational` 时类型设 5（`pillow_3ac9_K1_rational_type_5.patch`） | 1（主审：合理替代） | 1（11/11） | — |
| 同上 | K1b：同 K1，类型设 10（`pillow_3ac9_K1b_rational_type_10.patch`） | 1（主审） | 1（11/11） | — |
| 同上 | K2：只在值全是分母为 0 的 `IFDRational` 时设 5（`pillow_3ac9_K2_zero_denominator_only.patch`） | 1（主审：部分实现） | **1**（11/11） | — |
| 同上 | K3：只给 `IFDRational` 加 `__index__`（`pillow_3ac9_K3_index_on_rational.patch`） | 0（主审：错误实现） | 0（10/11） | `TestFileTiffMetadata.test_exif_div_zero`（FAILED） |
| 同上 | K4：只在 `TAGS_V2` 登记 `41988: ("DigitalZoomRatio", RATIONAL, 1)`（`pillow_3ac9_K4_tag_len_1.patch`） | 0（主审：满足题面文字、违背示例） | 0（10/11） | `TestFileTiffMetadata.test_exif_div_zero`（ERROR） |
| 同上 | K4b：同 K4，长度写 0（`pillow_3ac9_K4b_tag_len_0.patch`） | 1（主审） | 1（11/11） | — |
| 同上 | 复核者 C6：gold，但 `isinstance(v, IFDRational)` 换成 `isinstance(v, Rational)`（`numbers.Rational`，int 也算；`pillow_3ac9_RC6_gold_with_numbers_rational.patch`） | 1（复核者：错误实现） | **1**（11/11） | — |

## 2. 语义复核（不计入 reward）

**numpy `5e8301c2`**：两条手动命令，在一次性容器里应用候选后执行（`numpy5e83_extra/`）。

| 条件 | 交换操作数顺序：`np.einsum('ti,ti->i', np.ones((1,2)), np.ones((10,2)), optimize=True)` | 求和维度长度为 1 走 BLAS：`'ij,jk->ik'`，形状 (2,3) 与 (1,4) |
| --- | --- | --- |
| gold | `[10. 10.]` | **`ValueError: shape-mismatch for sum`**（`numeric.py` 的 `tensordot`） |
| C-C | **`ValueError: Size of label 't' for operand 1 does not match previous terms.`** | **`ValueError: shape-mismatch for sum`** |
| C-A | `[10. 10.]` | 与 `optimize=False` 结果一致（`True`） |

C-C 只修了题面这一种顺序，评分仍给 1；gold 本身也没修好求和维度走 BLAS 的路径。

复核者（`review.md`）另指出一个更简单的未修情形，协调者在同样条件下核对（`numpy5e83_extra/extra2_*.json`）：本 base 的 `einsum` 默认 `optimize=True`（源码 `kwargs.pop('optimize', True)`），所以不传 `optimize` 也会走优化路径。

| 条件 | `np.einsum('i,i', [2., 3.], [4.])`（不传 optimize） | 同上，`optimize=False` |
| --- | --- | --- |
| base | `ValueError: Size of label 'i' for operand 1 does not match previous terms.` | `20.0` |
| gold | **`ValueError: shape-mismatch for sum`** | `20.0` |
| C-A | `20.0` | `20.0` |

**coveragepy `97997d2c`**：`postcheck/coveragepy_97997d2c_paths.py`，三项检查：直接对 `CoverageConfig` 读写 `"paths"`（插件拿到的就是它，题目标题是 "via Plugins"）；经 `Coverage.set_option` 设置后 `cov.config.paths` 是否更新（`combine()` 读的是它）；真实 `combine()` 能否把 `/src/pkg/a.py` 映射成 `/dst/pkg/a.py`。

| 条件 | `CoverageConfig` 读写 | `cov.config.paths` 更新 | 真实 `combine()` 映射 |
| --- | --- | --- | --- |
| base | 失败 | 失败 | 失败 |
| gold | 通过 | 通过 | 通过 |
| W1 | **失败**（`CoverageConfig.set_option` 仍不认 `"paths"`） | 通过 | 通过 |
| W2 | 通过 | **失败** | **失败**（设置的值没进 `combine()`） |
| A1 | 通过 | 通过 | 通过 |

W1、W2 都得 1，但各漏了一半需求：W1 修不到插件拿到的配置对象，W2 设进去的值不生效。

替换还是合并（`private_public_b2/cov9799_rvm_*.json`）：临时目录写 `.coveragerc`，`[paths]` 段含 `first = /first/1 /first/2`，构造 `Coverage()` 后 `set_option("paths", OrderedDict([("magic", ["src", "ok"])]))`。gold 与 W1 之后只剩 `magic`；M 之后是 `first` 加 `magic`。隐藏测试从空 `paths` 起步，两种语义都得 1。

**orange3 `4014f248`：构建后私有比对**（`postcheck/private_regrade_build.py`，`private_regrade/o4014_*.json`）。应用补丁，可选先执行 `.venv/bin/python setup.py build_ext --inplace`，再像评分那样放入隐藏测试运行，用评分同一解析器逐键比对。与正式评分的差异：以 root 运行，不走评分的阶段与预算。

| 条件 | 构建 | 期望键匹配 |
| --- | --- | --- |
| C2，不构建 | — | 26/27（只有 `TestEqualFreq.test_below_precision` 不符，与正式评分一致） |
| C2，先构建 | 成功（`[1/1] Cythonizing Orange/preprocess/_discretize.pyx`） | **27/27** |
| gold，先构建 | 成功 | 27/27 |

C2 是正确修复：构建后逐键与期望一致。正式评分给 0，是因为评分不重新编译（`RH2_INSTALL_SKIPPED=1`），而交付的补丁只带 `.pyx`，不带编译产物。

**以 agent 身份走一遍（复核者提的最小实验，09-25 下午）**：用正式启动路径 + 真实 CC + 桩端点，以 agent（uid 54321）依次执行：题面复现 → 只改 `.pyx`（与 C2 相同）→ `python setup.py build_ext --inplace` → 再复现 → 列出导出补丁会含的文件。证据在 `runs/r2e_actor_20260925/devcheck/orange3__4014f2483e3bab0621c9ae0f994947c/{agentpath,agentpath2}/`。

- **agent 重建失败**：Cython 转换与编译成功，链接失败，`/usr/bin/ld: cannot find -lpython3.7m: No such file or directory`。原因是派生镜像把解释器搬到了 `/opt/py/cpython-3.7.9-linux-x86_64-gnu/`（那里有 `libpython3.7m.so`），但解释器的 `sysconfig` 里 `LIBDIR` 仍是搬迁前的 `/root/.local/share/uv/python/cpython-3.7.9-linux-x86_64-gnu/lib`，而 `/root` 是 `drwx------`，agent 进不去。root 能构建成功（上表），是因为 root 能读 `/root` 下的原路径。
- **更正**：本页上一版写"agent 可以自己构建并在本地看到测试通过（devcheck 的 `pr9_8_cmd` 证明 `build_ext` 可用）"，这是错的。`pr9_8_cmd` 在 base 上跑，源码没改，`build_ext` 只是把已有的 `.so` 复制回去，没有编译和链接。
- 重建失败后再复现，仍是题面的 `AssertionError`（旧 `.so` 还在）。所以只改 `.pyx` 的 agent 既不能在本地验证，交付后评分也不会重建，两头都拿不到正确结果。
- **导出**：`.so`、`_discretize.c`、`build/` 都在 `.gitignore` 里，正式导出脚本（`git add -N .` 加 `git diff --binary HEAD`）不会带上它们，补丁里只有 `.pyx`。另：本次核对的启动路径没有写 `/rh2/base_untracked.txt`，所以导出里还多了镜像自带的 `datasets`、`install.sh`、`run_tests.sh`；正式 rollout（`adapters/slime/generate.py`）在 harness 动工前写这份清单并按清单排除，这三项是核对路径的差异，不是正式路径的问题。

**aiohttp `1c1c0ea3`：cleanup 错误去向**（`postcheck/aiohttp_1c1c0ea3_cleanup_error.py`，`postcheck_b2/a1c1c_*.json`）。app 的 cleanup_ctx 在 `yield` 之后抛 `RuntimeError("cleanup failed")`，`run_app` 的 `print` 回调用 `loop.call_soon` 抛 `KeyboardInterrupt`，装一个记录调用的异常处理器。

| 条件 | 结果 |
| --- | --- |
| base | 报告：处理器收到 1 次（`unhandled exception during asyncio.run() shutdown`，`RuntimeError('cleanup failed')`），`run_app` 正常返回 |
| gold | 抛出：`run_app` 抛 `RuntimeError: cleanup failed`，处理器未被调用 |
| C1 | 报告（同 base） |
| C3 | **丢失：既没报告，也没抛出** |
| C5 | 报告（同 base） |

C3 得 1，但把 Ctrl+C 之后 cleanup 的错误静默丢掉；56 个键都测不到。

**numpy `a5ea773e`：`tile` 的形状与内存共享**（`private_public_b2/na5ea_sem_*.json`；本 base 没有 `np.shares_memory`，用 `np.may_share_memory`）。`a = np.arange(5)`，`b` 为 2×3，`z = np.array(7)`：

| 条件 | `tile(a, 1)` | `tile(a, (1,))` | `tile(a, [1])` | `tile(a, (1, 1))` | `tile(b, 1)` | `tile(z, 1)` |
| --- | --- | --- | --- | --- | --- | --- |
| base | (5,) 共享 | (5,) 共享 | (5,) 共享 | (1, 5) 共享 | (2, 3) 共享 | (1,) 共享 |
| gold、A | (5,) 不共享 | (5,) 不共享 | (5,) 不共享 | (1, 5) 不共享 | (2, 3) 不共享 | (1,) 不共享 |
| B | (5,) 不共享 | **(5,) 共享** | **(5,) 共享** | **(1, 5) 共享** | (2, 3) 不共享 | **() 形状错** |
| C | (5,) 不共享 | (5,) 不共享 | (5,) 不共享 | **(5,) 形状错** | (2, 3) 不共享 | **() 形状错** |
| 复核者 C2 | (5,) 不共享 | (5,) 不共享 | (5,) 不共享 | **(1, 5) 共享** | (2, 3) 不共享 | (1,) 不共享 |
| 复核者 C3 | (5,) 不共享 | (5,) 不共享 | (5,) 不共享 | **(5,) 形状错** | (2, 3) 不共享 | **() 形状错** |
| D | 共享 | 共享 | 共享 | 共享 | 共享 | 共享 |

B、C 与复核者的 C2、C3 都得 1：唯一目标键只测题面这一种写法（`reps=1` 的 1-D 数组）。

**datalad `19f5b450`：公开侧对照**（`private_control_full.py` 应用候选后跑公开读者的 pr1 与 pr4，`private_public_b2/d19f5_*.json`）。pr1 依次跑五种情形，打印进程退出码：

| 条件 | `run --explicit 'exit 3'` | `run 'exit 3'` | `run --explicit 'exit 0'` | `-i does-not-exist`（输入缺失） | `--on-failure ignore` | pr4（`test_run.py` 两例 + `test_rerun.py` 一例） |
| --- | --- | --- | --- | --- | --- | --- |
| gold | 3 | 3 | 0 | 1 | 0 | 全过 |
| K1 | 3 | 3 | 0 | 1 | 0 | 全过 |
| K2 | 3（不再输出 `run(error)` 结果行，改由 stderr 一行 `CommandError: 'exit 3' failed with exitcode 3` 报告） | 3（同左） | 0 | 1 | **3** | **`test_basics`、`test_run_failure` 失败** |
| K3 | 3 | 3 | 0 | **None（进程以 0 退出）** | 0 | 全过 |
| H | 3 | 3 | 0 | **3** | 0 | 未跑 |

K2 改了 Python API 的行为，公开测试能发现，隐藏测试发现不了；K3 在输入缺失时退出码变成 0，H 在输入缺失时退出 3，公开与隐藏测试都发现不了。

**pillow `3a61c9e9`：主审附录的私有命令**（`private_public_b2/p3a61_*.json`；C2 是题面恒等映射加 C 层检查，C3 是两项交换，C4 是显式传入 RGB `source_palette` 的 GIF 路径）：

| 条件 | C2：`getpalette(None)` 长度（原图 / 结果）、RGBA 渲染一致 | C3：交换后模式与前 8 字节、渲染一致 | C4：GIF 往返一致 | 完整 `Tests/test_image.py` |
| --- | --- | --- | --- | --- |
| gold、C1 | 1024 / 1024，一致 | RGBA，`[50, 60, 70, 80, 10, 20, 30, 40]`，一致 | 一致 | 71 passed / 1 skipped |
| W1 | 同 gold | 同 gold | **不一致** | 71 passed / 1 skipped；`Tests/test_file_gif.py` 73 passed / 2 skipped（公开 GIF 测试也发现不了） |
| W2 | **1024 / 768，不一致**（C 层丢了 alpha） | RGBA，前 8 字节同 gold，**渲染不一致** | 一致 | 71 passed / 1 skipped |
| W3 | 同 gold | **RGB，`[50, 60, 70, 10, 20, 30]`，渲染不一致**（非恒等映射仍是 base 行为） | 一致 | 71 passed / 1 skipped |
| W5 | **原图与结果都变成 RGB**，768 / 768，"一致"（两边都已丢 alpha） | RGB，`[50, 60, 70, 10, 20, 30]`，"一致" | 一致 | 71 passed / 1 skipped |

W1、W2、W3、W5 都得 1：隐藏测试只比较恒等映射后的 Python 层调色板字节，而且在调用之后才读原图的调色板，所以就地改坏原图（W5）也测不出来。


**scrapy `e9387529`：E1（gold 回归对照）与公开读者命令 B**（`private_public_b2/se938_*.json`）。E1a：`binary=True, export_empty_fields=True` 导出缺字段的 item；E1b：`binary=True`，字段 serializer 返回 int；E1c：`binary=False` 对照。命令 B 第 1 行是 item 里嵌套普通 dict，第 3 行是顶层 dict item。

| 条件 | E1a | E1b | E1c | 命令 B 第 1 行（嵌套） | 命令 B 第 3 行（dict item） |
| --- | --- | --- | --- | --- | --- |
| base | `{'age': None, 'name': b'x'}` | `{'name': b'x', 'age': 22}` | `{'age': None, 'name': 'x'}` | 全是 str 键 | str 键 |
| gold | **`TypeError: to_bytes must receive ... got NoneType`** | **`TypeError: ... got int`** | 同 base | 全是 bytes 键 | bytes 键 |
| C1 | `{b'age': None, b'name': b'x'}` | `{b'name': b'x', b'age': 22}` | 同 base | item 键 bytes，嵌套普通 dict 的键仍是 str | bytes 键 |
| C2 | 同 C1 | 同 C1 | 同 base | 同 C1 | **str 键** |
| 复核者 C2 | 同 C1 | 同 C1 | 同 base | 全是 bytes 键（同 gold） | bytes 键 |

gold 在 E1a、E1b 两种情形抛 `TypeError`（base 与 C1 都不抛），隐藏测试不覆盖；C2 对 dict item 不生效，也得 1。

**coveragepy `ea6906b0`：`.gitignore` 是否真的起作用**（`private_public_b2/cea69_*.json`）。临时 git 仓库里 `coverage run` 一个小脚本再 `coverage html`，看 `htmlcov/.gitignore` 的大小与 `htmlcov/` 下还有多少文件出现在 `git status` 的未跟踪列表里（镜像 Python 3.7.9）：

| 条件 | `.gitignore` 字节数 | `htmlcov/` 下仍未被忽略的文件数 |
| --- | --- | --- |
| base | 不存在 | 8 |
| gold | 27 | 0 |
| C-A | 2 | 0 |
| C-B | **0（空文件）** | **9**（报告文件与 `.gitignore` 自身都没被忽略） |

C-B 什么都没忽略，仍得 1：隐藏测试里与 `.gitignore` 有关的只有一句 `self.assert_exists("htmlcov/.gitignore")`（`hidden_tests/test_1.py:147`），不查内容。

**aiohttp `22a12cc2`：经 HTTP 代理 CONNECT 的真实握手**（公开读者的 C4 脚本，devcheck `pr4_7_cmd`；`private_public_b2/a22a1_*.json`）。本地起 HTTPS 源站与 HTTP 代理，分别用错误指纹直连、正确指纹经代理、错误指纹经代理（connector 级与单次请求级）：

| 条件 | 直连 + 错指纹 | 代理 + 对指纹 | 代理 + 错指纹 | 代理 + 错指纹（单次请求） |
| --- | --- | --- | --- | --- |
| base | 抛 `ServerFingerprintMismatch` | 连通 200 | **连通 200** | **连通 200** |
| gold、K1、K2 | 抛 | 连通 200 | 抛 | 抛 |
| K3 | 抛 | 连通 200 | **连通 200（同 base）** | **连通 200（同 base）** |
| K4 | 抛 | **抛（对指纹也被拒）** | 抛 | 抛 |

K2 在真实握手上与 gold 完全一致，评分却给 0：目标测试把 `connector._get_fingerprint` 换成 Mock，不经这个 helper 取指纹的实现就判错。候选语义已按第二批规则实测核过，这是测试与实现细节耦合造成的误拒；它算不算"合理"修复（仓库里已有 `_get_fingerprint` 这个 helper）以复核结论为准。反过来，K3 实际什么都没修、K4 连正确指纹也拒绝，都得 1。

**coveragepy `ea6906b0`：无数据时是否建目录**（`private_public_b2/cea69_nd_*.json`）：base 与 gold 在没有覆盖数据时 `coverage html` 报 `No data to report.`、rc=1、不创建 `htmlcov/`；复核者的"提前写 `.gitignore`"候选同样报错，但 `htmlcov/` 已被创建，评分仍给 1。公开旧测试 `tests/test_coverage.py::ReportingTest::test_no_data_to_report_on_html` 在 gold 下通过、在该候选下 FAILED（`private_public_b2/cea69_pt_*.json`），即 agent 跑公开测试能发现，隐藏测试不含这条。

**aiohttp `22a12cc2`：复核者 C（gold 改用 `abort()`）** 在真实握手上与 gold 一致（`private_public_b2/a22a1_aiohttp_22a1_RC_gold_but_abort.json`），评分给 0，原因是测试替身没实现 `abort()`。连同上面的 K2，这道题有两个语义正确的实现因测试替身细节被判 0。

**scrapy `75450e75`：E1（槽位累计后是否挂起）与 C2（槽位是否空闲）**（`private_public_b2/s7545_*.json`）：

| 条件 | E1：rc / stdout / crawled / 报错数 | C2：`(…, is_idle())` / 报错数 |
| --- | --- | --- |
| base | 0 / `FIRST_DONE`、`SECOND_DONE`、`(None, None, None, None)` / 2 / 4 | `(None, None, True)` / 2 |
| gold | **124（60 秒超时）/ 只有 `FIRST_DONE` / 1 / 0** | **`(None, None, False)`** / 0 |
| K1、K1b | 0 / 同 base / 2 / 0 | `(None, None, True)` / 0 |

gold 把报错去掉了，但协程排在一个从不运行的事件循环上：槽位不空闲，累计超过 `SCRAPER_SLOT_MAX_ACTIVE_SIZE` 后第二次 fetch 永久挂起。K1、K1b 两次都完成且无报错。掩盖型 K3 也得 1。

**pillow `3ac9396e`：非零分母能否保存**（`private_public_b2/p3ac9_*.json`；未注册 tag 41988 分别存 `IFDRational(0, 0)` 与 `IFDRational(1, 2)`，保存后读回）：

| 条件 | 分母为 0 | 分母非 0 |
| --- | --- | --- |
| base | 抛 `struct.error: required argument is not an integer` | 同左 |
| gold、K1 | 保存成功，读回 `(nan,)`，类型 5 | 保存成功，读回 `(0.5,)`，类型 5 |
| K2 | 保存成功 | **仍抛 `struct.error`** |

K2 只修了题面那种分母为 0 的情形，得 1；题面把原因说成"零分母"，实际非零分母同样失败。

未注册 tag 65000 = 5（int）保存后读回（`private_public_b2/p3ac9_ir_*.json`）：base `(5,)`、类型 4（LONG）；gold `(5,)`、**类型 3（SHORT）**（gold 顺带改了整数的类型推断，没有测试覆盖）；K4b `(5,)`、类型 4；复核者 C6 **`(5.0,)`、类型 5（RATIONAL）**，整数被当成有理数写入，仍得 1。