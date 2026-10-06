# 新 CPU 机的镜像与输入准备

2026-10-03。资源由总协调开放，本包所有 Docker 准备均使用 `cpu_slot.py --mode prepare`，每次新作业ID；包装器等整个准备进程退出后释放槽。题级 CPU profile 沿用既有 2 CPU／4 GiB，不在本文件改变。

当前结果见 [image_results.json](image_results.json)。六题均已完成固定摘要拉取、八个公开 wheel 的内容／大小校验、断网构建和 base 层保留检查，实际derived ID与全部证据SHA已归档。先前繁忙75记录保留，不算运行失败或题目负对照。

本轮使用 [image_plans.json](image_plans.json)、[wheelhouse_manifest.json](wheelhouse_manifest.json)、[Dockerfile.wheelhouse](Dockerfile.wheelhouse) 和 [prepare_image.py](prepare_image.py)。其中 registry manifest 和 base config ID 分别来自本题原输入／历史准备记录，core 版本逐题核对本题 base 的 `pyproject.toml`，不借用8793。6283／5662的原基础镜像Python/core与源码已由实际actor验证；其它四题的运行身份及六题候选安装仍待完成。实际派生镜像的候选安装不能仅由base层保留推定通过。

八个公开 wheel 的 SHA／字节与原 `pydantic_v1/assets_manifest.json` 一致，已排除1021字节私有 canary；派生镜像属于这一明确范围的恢复，不能写成原历史派生ID重建成功。构建步骤不改原 Python/core 或目标项目，不预先应用 gold／私有测试。

远端输入位于本包 `preparation_v1`；[upload_manifest.json](upload_manifest.json) 的138个文件在远端逐项对账。它是本包草案的传输快照，不是共用 release，也不是受信材料登记。5662／6283 的[非作者材料静态窄核](../reviews/non_author_5662_6283_review_20261003.md)已完成，无新增阻断；另外四题待排。正式评分仍须绑定共用维护者确认的不可变源码／材料版本；新consumer、候选矩阵、公开 actor、运行后复核和 GPU 提交目前均未完成。

另准备六份中性公开开发说明，路径及摘要见 [public_notes_manifest.json](public_notes_manifest.json)，仅用公开解释器、依赖元数据与仓库现有测试文件。未包含gold、私有断言或错误候选设计；这些仍是待运行事实确认的草稿，未改变原公开题面，也未提交探针。

优先两题的[正式CPU执行计划](cpu_acceptance_plan.json)已固定各材料／镜像、四方或三方矩阵与逐参考要求；`shared_release` 仍为null，不构造不存在的正式版本。公开actor必须实际交付原题面／public_hints，不能以默认devcheck控制提示代替。

首份基线release已受信核对，可用于已登记原材料诊断；[actor诊断入口](../cpu_diagnostics_20261003/README.md)记录了旧runtime缺torch的零请求失败，以及新runtime下6283／5662实际公开交付和开发命令已完成。本包新测试正式消费仍未发布，镜像准备完成不等于安装或题级验收。

完整日志和 slot 状态保留在忽略运行目录 `runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/`，各结果记录给出具体相对路径与 SHA；连接凭据不进入本包文档。
