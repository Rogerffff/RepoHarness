# DVC5839 当前题卡

2026-10-03。状态：**R10正式noop正常评分0，gold正常评分1，固定8位错解运行中。** R10共享UID修复已部署，旧R7／R8／R9不得派发本题。公开actor及非作者正式原件读回尚未完成，未提交GPU。私有候选诊断和材料核查可复用；当前结果见[formal_cpu_r10_v1.json](formal_cpu_r10_v1.json)，固定输入见[revision.json](revision.json)。

公开要求是 `metrics show --precision n` 按小数点后n位生效，默认5。源码帮助与旧helper测试消解题面科学记法的疑问，不改为有效数字。标量float原本不舍入，不追加成该题必修目标。

历史可复用：09-25 actor_v2固定pathspec0.8.1，五种真实CLI及窄测试已验证；10份历史成功候选与gold输出一致，DeepSeek失败候选是有效数字过修。证据见 [09-29逐题复核](../../../../../swegym40_status_20260929/reviews/dvc_conan_dask.md)及 [原题卡](../../../../../swegym_task_audit_20260920/quality_batch01_20260921/results/iterative__dvc-5839/card.md)。这些不等于新宿主已准备。

本轮仅补一个F2P：真实YAML经命令解析和 `CmdMetricsShow.run()`，直接核默认5、非示例3、8及Markdown的数值。没有mock格式化helper，不限制传参方式或表格空格。原F2P/P2P保留。准备 `hardcoded_precision8.patch`，只把gold传入的precision换成8；它违背默认/任意n要求，但**原正式评分未做，不能写已经得到1**。

cpu-a 私有诊断结果见 [cpu_diagnostics_v1.json](cpu_diagnostics_v1.json)：原版22节点和草案23节点均实际收集，引用无缺席。原版noop仅原F2P失败，gold及固定8候选22节点全过；草案noop两个F2P失败，gold23节点全过，固定8仅新增F2P失败。所有21个P2P保持通过，六次容器清理成功。这证明此草案有区分力，**还不是正式reward或环境资格**。

依赖准备固定原manifest/config摘要，4个wheel与历史SHA一致，构建保留base层且源码工作区不变；`pip check=0`。本轮实际导入 `/testbed/dvc/__init__.py`，pathspec0.8.1。新增 [有效安装配方草案](effective_install_recipe.json) 把该pin落实到真实安装段；[公开开发说明](public_development.md) 不含私有测试或候选信息，正式actor交付仍待核。

当前正式矩阵使用冻结R10 `cat2-cpu-r2e089092-swe14-preflight-20261003-v1`、同一成功prepare及同一新summary。noop→0（2F失败／21P通过）、gold→1（23节点全过）已经实际验证，UID54322依赖预检、安装、测试和两层清理正常；固定8位错解尚在运行。旧原材料的固定8正式reward未取得，私测原版全过只能作为历史诊断，不将新prepared改绑到旧FrozenPatch。

[非作者材料窄核](../../reviews/non_author_5839_material_review_20261003.md) 已完成：公开依据、原AST保持、逐参考诊断和配方返回语义均无静态阻断；该报告不替代正式评分、镜像或actor验收。

共用消费者已实现完整补丁替换、新增F2P、现有pytest文件选择及精确离线安装配方。R7 的安装前 UID54322 检查在实际 profile 中失败，须修正执行方式后重新验证完整安装；独立读取通过不替代该验收。原E13配方没有显式pathspec pin，不能当作已交付两侧一致环境。通过CPU、actor条件及非作者结果核查后提交单题探针请求，回传由本线程分析。

[R7 正式尝试与权限原件](formal_cpu_r7_v1.json)：root 核四 wheel SHA 成功，但 root 在受限 profile 中的 `os.setgroups/setgid/setuid` 均被拒绝；setup 因此退出3。另一个同标准 profile 的私有诊断通过真正 `docker exec --user 54322:54322` 读四 wheel，SHA 全匹配，确认读取权限本身可用。共用维护者已确认 setup 设计缺陷并接手冻结修复。本包未放宽权限，正式 gold／固定8及 actor 未启动；自有容器全部清理。当前支持请求为 `dvc5839-uid-preflight-support-20261003-v1`，固定[支持输入](../../requests/dvc5839_cpu_support_v1.json)已通知发布线程；新接续点见 [恢复记录](../../resume_checkpoint_20261003.md)，旧暂停记录保留。

R10共享UID修复已部署并回执核收；新prepared与同版成功prepare来源绑定。正式noop已正常评分0：候选UID54322固定四wheel预检通过、安装0、实际2F失败／21P通过、无missing／skip；两层清理及本job label无残留，31原件本机SHA归档。见[新正式记录](formal_cpu_r10_v1.json)。gold已正常评分1、23节点全过、32原件SHA归档；固定8位错解、公开actor和非作者正式原件读回仍未完成，未提交GPU。旧R7 infra原件保留。
