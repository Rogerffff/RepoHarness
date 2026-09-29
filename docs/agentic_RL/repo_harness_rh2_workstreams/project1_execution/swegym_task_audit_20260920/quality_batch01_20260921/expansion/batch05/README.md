# 第五批后备：2题材料已备，未派发

固定名单：`python__mypy-11707`、`getmoto__moto-5406`。同一原not_reviewed池排除B1–B4全部38题后，mypy剩30题、Moto剩52题；按`SHA256('swegym-quality-batch05-20260921|' + instance_id)`各取首题。不加DVC/Pandas，不扩池或换题。完整排除与排序见 [batch_manifest.json](batch_manifest.json)，其准备状态保持冻结；根另决定是否启用。

材料位于`runs/swegym_quality_batch05_20260921_v1/`，public/private/history隔离。[material_check.json](material_check.json)为本次导出检查的原样副本：6个原始源行、3,426个base blob（36,383,153字节）、26个执行文件、2个prompt、4个noop/gold日志引用均核验；base无.git。Moto5406额外1个gitlink固定commit列于base_identity，内容未导出；无symlink/LFS。未重复前批blob核验，未项目导入或运行。

[环境说明](environment_replay_notes.md)与[私有入口清单](environment_replay_inventory.json)区分mypy派生安装镜像和Moto原baseline，并保留runtime未知。[最小交接](handoff.md)仅供根任务启用时定位材料；没有dispatch或审查结果。

manifest SHA256：`ea9421d30ba7bbf9078dc42967f8f5eaa7cc0554a7db19b6aa85bb48d1be9174`。本批仅静态准备，未审题、派发、运行项目/测试/网络/容器/模型，也未改变前四批、源数据或root orchestration。
