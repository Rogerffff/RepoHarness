# reserve6 Pydantic8567/9066：发车前独立窄审

2026-09-29。**未发现阻断，可以按本版运行。** 这是跨包独立静态审查，复用既有运行/脚本上下文，不是 fresh 盲审；没有运行目标项目、容器或远端，也没有修改作者脚本/输入。结论只覆盖本轮编排的可执行性与防误判条件，不证明环境或题目合格，不宣称 OS 隔离。

核对的[新脚本](../../../../../../rh2/experiments/swegym_cpu_preprobe_20260929/pydantic_reserve_followups_v1.py) SHA 为 `d0121ce567a51568822c66bd846fe398badce55bc82317b5309e61e81cf6559e`；输入清单 [8567](../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs_reserve6_v1/pydantic__pydantic-8567/input_manifest.json)／[9066](../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs_reserve6_v1/pydantic__pydantic-9066/input_manifest.json) SHA 分别为 `8698a3fd54f715d5c87c67d165f981e2a9e92424ebf3ee7cf3ed9d59f2242b55`、`1975a6aee7f2a8968914b22ec7cf7384b349ba69deee5c0dd092349b4ff90374`。独立核了20份清单文件、冻结直接入口 SHA、JSON/AST/bash语法，gold 与 reserve6 导出逐字一致；不以作者 static_validation 报告替代这些核对。

## 判据与材料边界

- **8567**：公开命令保留题面两种 Annotated 顺序，核内部 bool、Python dump 和 JSON dump；base 的 y=true 必须在指定最终断言失败，gold 必须两个输出均为字符串。固定 base 要求 core2.15.0，与公开 pyproject 一致；不套题面旧报告的2.14.6。私有 Custom+PlainValidator 在默认空 config 下，base 要求构造成功且保留同一对象；gold 要求类定义阶段的 `PydanticSchemaGenerationError/schema-for-unknown-type` 和精确消息前缀。gold 新增 `handler(source_type)` 正是待验证路径，不能将任意异常归作该回归。
- **9066**：公开 IP 默认值控制要求 base 的精确警告与缺 default，gold 要求正确 default 且无警告，均核 schema 类型/format。core2.16.3 与对应 base 一致。私有标准 dataclass 实例 default 先核 Model 正常实例化；base 要求 schema default={x:1}，gold 要求 `model_json_schema` 阶段的 `PydanticUserError/type-adapter-config-unused`。对应 base 的 TypeAdapter 明确在 dataclass 且 config 非 None 时抛此错误，gold 将空 config 传入该路径；运行前仍只是待证假设。

公开命令只有公开题例、身份和旧测试；私有 Custom/dataclass 控制与 gold 仅交私有 helper，未传 devcheck。没有为了数量新增退化：本轮先验证 gold 的具体兼容性风险。私有观测是 root 身份，不替代 actor 权限或模型实际接收完整题面的证明。

## 安装、退出与清理

两份 revised_install 与各题09-19 gold recipe 逐字相同：实际 editable 安装候选，再消费候选 testing/testing-extra 元数据；前一安装失败会返回，不被末尾成功命令吞掉。8个公开构建 wheel 固定 URL/尺寸/SHA，排除私有 canary；新派生镜像仅 COPY/离线环境层，保留原 base 层，不声称恢复了历史派生 image ID。基础 config ID/core 在 actor、私有与 grader 观察中分别核对；没有增加 core 升级或全环境 pip-check 的通过声明。

actor 要求 prelaunch/activation、完整日志、命令顺序、非截断 capture，并逐命令判精确行为；不是只看 all_match_expect。私有 matrix 在每个内层命令结束后检查输出，未知异常、超时、导入/收集故障或阶段不符会中止，外层 helper 0 不能替代完整 matrix 标记。源码 apply 后记录完整文件 SHA，便于实际读回；prepare/collect-only 失败亦停。

正式仍使用 reserve6 prepared/private/gold 与 code_v1；参考数为8567的1F2P/158P2P、9066的2F2P/367P2P。要求 install/test 段完成、apply_ok、参考不缺席、runner 摘要不变和真实 import/core；noop/gold 异常得分即停。候选容器 removed 和 manager 的 created=removed=1、容器/供应/清理集合为空、final exit0 均检查。SIGINT/TERM 转发进程组并留180秒清理；强杀记录 cleanup_unconfirmed 后停止，不能继续下一候选。资源2CPU/4GiB，setup900、whole3600，未改变冻结测试预算或正式参考。

**回传后必须核的范围**：实际完整源码投影与私有 source SHA、每个旧测/正式参考及完整测试日志、镜像/安装输出和清理原件。脚本的 `executed_pending_review` 只是取证完成；新捕获若不符合静态分类，应保留原件并归因，不能放宽 matcher 后倒签旧成功。D6、公开目标范围、模型/训练资格均不由本次准予运行解除。没有为非阻断改进新增启动闸门。
