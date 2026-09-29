# 09-25 中性材料准备目录

工作区：`/Users/roger/Desktop/claude-code-verl-stage0h`。仅写本说明与 `preparation_catalog.json`；未选择首12题、未导出base、未创建manifest/assignments、未执行项目代码或测试。

池已核：216题 − 五批 `task_ids` 并集40题 = **176题**；不读取 `new_review_status` 的值作排除，也不把166题维修目录作候选池。Modin5940/6937保留在176总数中但不进入选择，隔离后174题。

| 仓库 | 剩余 | 本次材料范围 |
| --- | ---: | --- |
| Project-MONAI/MONAI | 26 | 原始公开标题、三源行号/hash、精确base、历史环境原件定位 |
| conan-io/conan | 10 | 原始公开标题、三源行号/hash、精确base、历史环境原件定位 |
| dask/dask | 12 | 原始公开标题、三源行号/hash、精确base、历史环境原件定位 |
| getmoto/moto | 51 | 仅ID/repo/base；Modin两题标隔离 |
| iterative/dvc | 25 | 仅ID/repo/base；Modin两题标隔离 |
| modin-project/modin | 5 | 仅ID/repo/base；Modin两题标隔离 |
| pydantic/pydantic | 18 | 原始公开标题、三源行号/hash、精确base、历史环境原件定位 |
| python/mypy | 29 | 仅ID/repo/base；Modin两题标隔离 |

四仓共66题；Git `show -s --format=%H%n%T` 精确commit可定位 66/66，尚未导出/逐blob验全；镜像实际工作树不是这些Git对象。历史环境定位 66/66题，共132份日志；本地文件hash不匹配 0题，路径缺失 0题；每题image inventory原件 35/66。这里只核定位与hash，没有阅读运行判定。

## 原始来源与边界

- `public`：`docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/public_bundles_v0.jsonl`，SHA-256 `278a52be906f4f5fe98418f5bfd6536e97b333b0fdc9bbd15cd1328ae8c5f7f3`。
- `grading`：`docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/grading_bundles_v2_v0.jsonl`，SHA-256 `762a3ad12a08e4c723bf5da609cf765a6a42388e01530d411dd61e82de625264`。
- `validation`：`docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/validation_bundles_v0.jsonl`，SHA-256 `196fdf81e1142c431d7b60dee5082db6ccfd3ba8b65f88f686bb12b2020ad961`。

JSON逐题保留三份原始bundle的1-based行号与不含换行的行hash。公开标题直接取真正公开 `problem_statement` 首个非空行，并验题面SHA-256；三源ID及public/grading repo/base对应已核。validation没有base字段，按ID关联。私有gold/test内容与旧质量标签未抄入目录。

环境材料只列历史grader输入的image/recipe/scripts身份、账本/日志定位及本地hash；维修目录只用于定位配方。recipe来源的历史结果不等于当前actor可用。实际actor初态、status/diff、忽略资产、消息、用户权限、主机镜像是否仍存在均为 `unknown`。未导出不等于镜像缺资产。每题具体定位和缺口见JSON。

## 建议复用的导出器

使用 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch05/prepare_materials.py`（SHA-256 `4111acc66afa1d1f13db5166cf0e267570f6a349ac3b81f2d8d062c075299aa7`）中的独立函数；不执行旧脚本整份main、不沿用其旧选池或环境BRIEF。它仅用stdlib并以AST核prompt，不需要导入RH2项目。

- `validate_public`：第18–25行。
- `render_user_prompt`：第28–33行。
- `verify_prompt_template`：第36–45行。
- `verify_base`：第99–157行。
- `export_base`：第160–221行。
- `ledger_refs`：第224–243行。

当前 `bundles.py` 的prompt返回表达式与该导出器AST一致：`True`。冻结明确题号后，按原行保留公开/私有输入，采用 `export_base` + `verify_base` 对拍blob、权限和文件集合；gitlink内容与LFS外部实物需单列缺口。不要将base包、渲染计划prompt冒称实际初态或实际消息。

较早首批准备器会导入项目；第三批虽有成熟blob验证，其旧 `verify_selection` 还依赖 `new_review_status`。两者不适合整份沿用本轮。

## 首12题供协调者定号的公开标题目录

| ID | 原始公开标题 | public行 |
| --- | --- | ---: |
| conan-io__conan-11560 | [bug] bazel generator not usable for packages with multiple libs, like openssl | 27 |
| conan-io__conan-11594 | [bug] `cmake.test()` cannot execute | 28 |
| conan-io__conan-12397 | [bug] Meson Toolchain does not add required `-stdlib` args to `cpp_link_args` | 29 |
| conan-io__conan-13230 | [bug] AutotoolsToolchain uses the build compiler rather than host compiler | 30 |
| conan-io__conan-13326 | [bug] qcc cannot calculate dep graph because it fails to produce a list of compatible cppstd per compiler verison | 31 |
| conan-io__conan-13403 | [bug] Can't specify Autotools.autoreconf() location to the build directory | 32 |
| conan-io__conan-13610 | Take a look into normalizing the log levels of conan | 33 |
| conan-io__conan-13721 | [feature] Add profile_name variable to profile rendering | 34 |
| conan-io__conan-13788 | Multiple versions of same build_requires package in lockfile? | 35 |
| conan-io__conan-14296 | [question] Using Ninja (Multi-Config) with Extending Own CMake Presets Example | 37 |
| dask__dask-10972 | test_encoding_gh601[utf-16] doesn't always fail | 39 |
| dask__dask-6626 | Index(['a', 'b'], dtype='object') instead of Index([], dtype='object') with set_index when empty categories in dataframe | 40 |
| dask__dask-6801 | dd.to_parquet with schema='infer' runs my code 4x | 41 |
| dask__dask-6818 | blocksize and persist has impact on result | 42 |
| dask__dask-7138 | Issue: dask.array.ravel currently requires an 'array' object as argument but should require an 'array_like' object | 43 |
| dask__dask-7305 | `partition_quantiles` finds incorrect minimum with large unsigned integers | 44 |
| dask__dask-7656 | dataclass issue with fields that have init=False | 45 |
| dask__dask-7894 | map_overlap does not always trim properly when drop_axis is not None | 46 |
| dask__dask-8792 | dask.base.clone_key loses prefix if it has no token | 48 |
| dask__dask-8820 | Support `__name__` on functions annotated with `@delayed` | 50 |
| dask__dask-9212 | Enum deterministic hashing | 51 |
| dask__dask-9378 | Mask preserving *_like functions | 52 |
| Project-MONAI__MONAI-1121 | Add TorchScript compatible test for all the networks | 1 |
| Project-MONAI__MONAI-2061 | Add support to compute metrics on list of images and tensor label | 2 |
| Project-MONAI__MONAI-2446 | SmartCacheDataset modified input datalist | 3 |
| Project-MONAI__MONAI-2454 | `ToTensor()` transform adds unexpected dim | 4 |
| Project-MONAI__MONAI-3205 | About class CrossValidation issues | 5 |
| Project-MONAI__MONAI-3403 | inconsistent output types for `correct_crop_centers` | 6 |
| Project-MONAI__MONAI-3547 | `set_determinism` can't work when disable_global_flags | 7 |
| Project-MONAI__MONAI-3566 | metadata when loading DICOM series | 8 |
| Project-MONAI__MONAI-3690 | Skip workflow run if no data provided | 9 |
| Project-MONAI__MONAI-3715 | `mode` of Evaluator can't work with string input | 10 |
| Project-MONAI__MONAI-4109 | Make `pixelshuffle` scriptable. | 11 |
| Project-MONAI__MONAI-6975 | `Lazy=True` ignored when using `Dataset` call | 24 |
| Project-MONAI__MONAI-763 | Incorrect operation of dense_patch_slices | 25 |
| Project-MONAI__MONAI-4159 | Checkpoint Export Functionality Should Require Bundle Directory Path Only | 12 |
| Project-MONAI__MONAI-4583 | a bug in convert_mask_to_box, will fail for multi-class detection | 13 |
| Project-MONAI__MONAI-4676 | Interoperability numpy functions <> MetaTensor | 14 |
| Project-MONAI__MONAI-4688 | collate_meta_tensor can't work with `ImageDataset` | 15 |
| Project-MONAI__MONAI-4775 | pytorch numpy unification error | 16 |
| Project-MONAI__MONAI-4925 | Improve FL ExchangeObject printing and summary | 17 |
| Project-MONAI__MONAI-5686 | SSIMLoss result does not have gradient | 18 |
| Project-MONAI__MONAI-5908 | SSIM loss fail when batchsize>1 | 19 |
| Project-MONAI__MONAI-5932 | `ConfigParser` can't get references with same prefix | 20 |
| Project-MONAI__MONAI-6523 | TypeError: unsupported format string passed to MetaTensor.__format__ | 21 |
| Project-MONAI__MONAI-6756 | get parsed content with default attribute error | 22 |
| Project-MONAI__MONAI-6775 | Bug of GeneralizedDiceLoss | 23 |
| Project-MONAI__MONAI-907 | sliding_window_inference() in monai.inferers went wrong when roi_size=(M,N,1) | 26 |
| pydantic__pydantic-5386 | No way to access fields during __init_subclass__ | 157 |
| pydantic__pydantic-5662 | BaseModel only matches other BaseModel's (not even unittest.mock.ANY) | 158 |
| pydantic__pydantic-6043 | Produce best-effort deterministically sorted json schemas | 160 |
| pydantic__pydantic-6104 | RootModel's `model_json_schema` miss field `title` and `description` | 161 |
| pydantic__pydantic-6126 | default_factory regression | 162 |
| pydantic__pydantic-6283 | Result of `RootModel.model_construct` is not equal to result of `RootModel.__init__` | 163 |
| pydantic__pydantic-8004 | Use `PrivateAttr` with `Annotated` will cause `AttributeError` when getting private attr. | 164 |
| pydantic__pydantic-8316 | `to_snake` alias generator bug -- great first issue | 165 |
| pydantic__pydantic-8500 | Model order not maintained when serializing after using model_construct with default values | 166 |
| pydantic__pydantic-8525 | Some properties do not remain private after constructing a serialised model | 168 |
| pydantic__pydantic-8567 | Annotated type PlainSerializer not used if placed before PlainValidator | 169 |
| pydantic__pydantic-8583 | OpenAPI discriminator field disapeared with pydantic v2.5 | 170 |
| pydantic__pydantic-8793 | model_json_schema export with Annotated types misses 'required' parameters | 171 |
| pydantic__pydantic-8977 | validate_call makes an unexpected conversion | 172 |
| pydantic__pydantic-9066 | Type `IPv4Address` not parsed | 173 |
| pydantic__pydantic-9134 | Using a private attribute in model_post_init of subclass | 174 |
| pydantic__pydantic-9193 | v2.7.0b1 throws error when using OpenAI SDK | 175 |
| pydantic__pydantic-9214 | RootModel.model_json_schema() ignores Field description | 176 |

未给推荐质量排名；请仅以公开类型与材料可定位性冻结题单。后续私有审查按原件先行，再开放历史。

## 阅读与执行记录

读了本批README、静态流程/协议、共用开发验证；这些方法文含历史例子，但未把例子作选题依据。读了旧准备器源码和manifest的source_files/repo_mirror投影；未打开逐题card/review/screening结论。索引、私有bundle、维修目录及账本经stdlib JSON机械解析后，仅输出允许的元数据；未语义审查gold/test或旧判定。

本轮只运行stdlib文件/JSON/hash/AST处理与只读Git show；无网络、下载、安装、Docker/SSH/GPU/模型、额度操作、commit/push。未读取或改写共享environment_batch页。

`preparation_catalog.json` SHA-256：`8115f3354ee418c5ae0af088ce389b70443b031993a21867422b1d9b512b5066`。
