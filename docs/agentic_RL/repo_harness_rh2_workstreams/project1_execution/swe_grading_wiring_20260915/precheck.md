# S1-p 静态控制面分类预检（gold 与真实候选）

生成：`precheck_gold_classification.py`。规则 = 生产 `HygieneRules`（official test 文件 + `DEFAULT_SWE_TEST_GLOBS` + 保留命名空间）。"忽略"= 可信评分投影不重放该路径（D2-3 排除法）；本表只做路径级分类，不判结构安全。

汇总：37 份补丁；全部被忽略 0 份；部分被忽略 21 份；其余无影响。

## A 组代表题 gold（9）

| 题 | 来源 | 重放路径 | 忽略路径（类别） | 预期影响 |
|---|---|---|---|---|
| conan-io__conan-13326 | gold | `conan/tools/build/cppstd.py` | （无） | 无影响 |
| dask__dask-7894 | gold | `dask/array/overlap.py` | （无） | 无影响 |
| getmoto__moto-6913 | gold | `moto/sesv2/responses.py` | （无） | 无影响 |
| iterative__dvc-5822 | gold | `dvc/repo/__init__.py` | （无） | 无影响 |
| modin-project__modin-6937 | gold | `modin/core/io/column_stores/parquet_dispatcher.py` | （无） | 无影响 |
| pydantic__pydantic-8500 | gold | `pydantic/main.py` | （无） | 无影响 |
| Project-MONAI__MONAI-6975 | gold | `monai/transforms/transform.py` | （无） | 无影响 |
| python__mypy-12741 | gold | `mypy/types.py` | （无） | 无影响 |
| pandas-dev__pandas-48106 | gold | `pandas/core/dtypes/cast.py` | （无） | 无影响 |

## C 组反例 gold（4）

| 题 | 来源 | 重放路径 | 忽略路径（类别） | 预期影响 |
|---|---|---|---|---|
| Project-MONAI__MONAI-1121 | gold | `monai/networks/nets/ahnet.py` | （无） | 无影响 |
| Project-MONAI__MONAI-3205 | gold | `monai/apps/datasets.py` | （无） | 无影响 |
| getmoto__moto-4799 | gold | `moto/core/models.py` | （无） | 无影响 |
| Project-MONAI__MONAI-763 | gold | `monai/data/utils.py` | （无） | 无影响 |

## B 组真实候选（24 条 DeepSeek 补丁）

| 题 | 来源 | 重放路径 | 忽略路径（类别） | 预期影响 |
|---|---|---|---|---|
| Project-MONAI__MONAI-2454 | DeepSeek 候选 | `monai/transforms/utility/array.py` | `tests/test_to_tensor.py`(official_test_file) | 部分被忽略；若被忽略路径承载修复则 gold/候选可能不通过 |
| Project-MONAI__MONAI-6975 | DeepSeek 候选 | `monai/data/dataset.py`, `requirements-dev.txt` | `tests/test_dataset.py`(official_test_file) | 部分被忽略；若被忽略路径承载修复则 gold/候选可能不通过 |
| conan-io__conan-13326 | DeepSeek 候选 | `conan/tools/build/cppstd.py` | `conans/test/integration/package_id/test_cache_compatibles.py`(test_glob), `conans/test/unittests/tools/build/test_cppstd.py`(official_test_file) | 部分被忽略；若被忽略路径承载修复则 gold/候选可能不通过 |
| conan-io__conan-14296 | DeepSeek 候选 | `conan/tools/cmake/presets.py` | `conans/test/integration/toolchains/cmake/test_cmaketoolchain.py`(official_test_file) | 部分被忽略；若被忽略路径承载修复则 gold/候选可能不通过 |
| dask__dask-7656 | DeepSeek 候选 | `dask/base.py`, `dask/delayed.py` | `dask/tests/test_base.py`(test_glob), `dask/tests/test_delayed.py`(official_test_file) | 部分被忽略；若被忽略路径承载修复则 gold/候选可能不通过 |
| dask__dask-7894 | DeepSeek 候选 | `dask/array/overlap.py` | `dask/array/tests/test_overlap.py`(official_test_file) | 部分被忽略；若被忽略路径承载修复则 gold/候选可能不通过 |
| getmoto__moto-5701 | DeepSeek 候选 | `moto/s3/responses.py` | `tests/test_s3/test_s3.py`(official_test_file), `tests/test_s3/test_server.py`(official_test_file) | 部分被忽略；若被忽略路径承载修复则 gold/候选可能不通过 |
| getmoto__moto-5899 | DeepSeek 候选 | `moto/iam/models.py` | `tests/test_iam/test_iam_groups.py`(official_test_file) | 部分被忽略；若被忽略路径承载修复则 gold/候选可能不通过 |
| getmoto__moto-6470 | DeepSeek 候选 | `moto/batch/models.py` | `tests/test_batch/test_batch_compute_envs.py`(official_test_file) | 部分被忽略；若被忽略路径承载修复则 gold/候选可能不通过 |
| getmoto__moto-6913 | DeepSeek 候选 | `moto/sesv2/responses.py` | `tests/test_sesv2/test_sesv2.py`(official_test_file) | 部分被忽略；若被忽略路径承载修复则 gold/候选可能不通过 |
| iterative__dvc-5822 | DeepSeek 候选 | `dvc/repo/__init__.py` | `tests/func/test_api.py`(official_test_file) | 部分被忽略；若被忽略路径承载修复则 gold/候选可能不通过 |
| iterative__dvc-9395 | DeepSeek 候选 | `dvc/commands/repro.py`, `dvc/stage/__init__.py` | （无） | 无影响 |
| modin-project__modin-6298 | DeepSeek 候选 | `modin/numpy/arr.py` | `modin/numpy/test/test_array_math.py`(test_glob) | 部分被忽略；若被忽略路径承载修复则 gold/候选可能不通过 |
| modin-project__modin-6937 | DeepSeek 候选 | `modin/core/io/column_stores/parquet_dispatcher.py` | `modin/pandas/test/test_io.py`(official_test_file) | 部分被忽略；若被忽略路径承载修复则 gold/候选可能不通过 |
| pandas-dev__pandas-48106 | DeepSeek 候选 | `doc/source/whatsnew/v1.5.0.rst`, `pandas/core/indexing.py` | `pandas/tests/series/indexing/test_setitem.py`(test_glob) | 部分被忽略；若被忽略路径承载修复则 gold/候选可能不通过 |
| pandas-dev__pandas-50319 | DeepSeek 候选 | `pandas/_libs/tslibs/parsing.pyx` | `pandas/tests/tslibs/test_parsing.py`(official_test_file) | 部分被忽略；若被忽略路径承载修复则 gold/候选可能不通过 |
| pydantic__pydantic-5706 | DeepSeek 候选 | `pdm.lock`, `pydantic/_internal/_std_types_schema.py`, `pyproject.toml` | `tests/test_edge_cases.py`(test_glob), `tests/test_types.py`(test_glob) | 部分被忽略；若被忽略路径承载修复则 gold/候选可能不通过 |
| pydantic__pydantic-8500 | DeepSeek 候选 | `pdm.lock`, `pydantic/main.py`, `pyproject.toml` | `tests/test_construction.py`(official_test_file) | 部分被忽略；若被忽略路径承载修复则 gold/候选可能不通过 |
| pydantic__pydantic-8793 | DeepSeek 候选 | `pdm.lock`, `pydantic/fields.py`, `pyproject.toml` | `tests/test_create_model.py`(test_glob) | 部分被忽略；若被忽略路径承载修复则 gold/候选可能不通过 |
| pydantic__pydantic-9214 | DeepSeek 候选 | `pdm.lock`, `pydantic/json_schema.py`, `pyproject.toml` | （无） | 无影响 |
| python__mypy-11236 | DeepSeek 候选 | `mypy/checkexpr.py`, `test-requirements.txt` | `test-data/unit/check-literal.test`(official_test_file) | 部分被忽略；若被忽略路径承载修复则 gold/候选可能不通过 |
| python__mypy-11352 | DeepSeek 候选 | `mypy/plugins/default.py`, `test-requirements.txt` | `test-data/unit/check-default-plugin.test`(official_test_file) | 部分被忽略；若被忽略路径承载修复则 gold/候选可能不通过 |
| python__mypy-12741 | DeepSeek 候选 | `mypy/checker.py` | （无） | 无影响 |
| python__mypy-16869 | DeepSeek 候选 | `mypy/stubgen.py` | `test-data/unit/stubgen.test`(official_test_file) | 部分被忽略；若被忽略路径承载修复则 gold/候选可能不通过 |

