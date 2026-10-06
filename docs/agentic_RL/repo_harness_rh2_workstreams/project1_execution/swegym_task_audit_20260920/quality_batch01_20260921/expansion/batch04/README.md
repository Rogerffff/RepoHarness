# 第四批后备：3题材料就绪，质量审查未开始

2026-09-21 05:29 SGT。固定题单为`iterative__dvc-4185`、`python__mypy-16869`、`getmoto__moto-6114`。尚未派发任何阅读角色；根任务依据B3进度、质量及07:30截止决定是否启用。

选题从同一原`not_reviewed`冻结池排除首批12题、B2十二题和B3十一题，再按`SHA256('swegym-quality-batch04-20260921|' + instance_id)`升序，DVC/mypy/Moto各取1题。三仓库剩余池分别26/31/53题；Pandas原池剩0题，不补题或扩池。原池、排除名单、全排序和来源hash见 [batch_manifest.json](batch_manifest.json)。

材料位于`runs/swegym_quality_batch04_20260921_v1/`，public/private/history分离；public只含原公开bundle、中性环境说明、静态构造prompt和精确base，无.git或未来历史。导出脚本只用标准库JSON/Git，prompt模板经当前源码AST对拍，不导入项目。

[material_check.json](material_check.json)记录本批导出及独立读回：9个源行、3,842个base blob（62,908,082字节）、40个执行文件、3个prompt、6个noop/gold账本与日志引用、3条history引用均核对。3,843个跟踪项中额外1项为Moto6114的`tests/terraformtests/terraform-provider-aws` gitlink，固定于`a8163ccac8494c5beaa108369a0c8531f3800e18`，内容未导出；无symlink或LFS指针。run目录共3,880文件，包含独立核验报告。

[原环境入口说明](environment_replay_notes.md)及[清单](environment_replay_inventory.json)仅供私有协调。DVC4185需要recipe、bindings及自定义networkx wheel条件；mypy16869/Moto6114沿install_wave1原CLI。目标镜像、重定位summary和运行环境仍待准备，未作actor验收或质量判断。

manifest SHA256：`6c27c2a0fd6a83be5c11076985e84421c8887f5ff801783db1564e8f20392c9b`。run清单摘要（排除随后写入的verification.json）：`b25a77137791e99f371aa1e1bf9758f402be94a8761570c63abbe6be3892a355`。仅修改本批两个新目录；未改首三批、原始证据、生产或root orchestration，未执行项目/测试/容器/SSH/下载/模型。
