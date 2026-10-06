# D6 原actor工件到fresh grader单条工具审查

2026-09-29。**无阻塞，可按已授权范围执行这一条10424真实actor noop工件。** 本结论只说明反例工具可执行，不提前认定F1已经远端复现或已修复。审查者只读本地代码及已有原件，未SSH、Docker、CC或评分，未改生产。

对象为 `runs/category2_repair_20260929/tools/d6_actor_to_grader_v1/actor_to_grader.py`、README与delivery manifest。脚本SHA-256为 `4f3cd3cfe9f76a1dd0934600f3fc772f6ab4d996b34276a61978816ab6b44685`，20323字节。独立核manifest列出的五项文件SHA及字节数均相符；重验冻结清单，并真实调用 `load_inputs` 和生产 `_verify_frozen_delta_binding`，全程无Docker调用。

## 原输入和语义未替换

- 固定actor记录清单SHA `eeef72964cf12abfd162a18ba9aa01401921f8cee23ebb931d3adc35738e54f0`，逐项核其28份原件SHA/字节数。baseline、frozen、projection直接从该原件解析，没有重生成、覆盖或拼接replay的baseline。
- 独立实际加载得到原actor baseline `sha256:e9d53030cc4462454733473159ddbc4c9044150847e9c3ff2039e3f865f8bfb7`、excluded摘要 `sha256:e782008a729129ee7cce7f35a9532ad75ed434dafbd6fe2306ea35c9cd976cbe`、frozen摘要 `sha256:cb02239f6c7b270a2342ae96a464778b285f7b1fdf67ab5ad0dc14c8bf448b4e`。这正是F1中待交付的actor工件，未换成已通过CPU路径的摘要。
- 同次CPU summary、profile、spec join各固定SHA；正式face核prepared/host/原assignment的公开与环境身份。材料上下文与原actor保存事实逐项相等，七项生产脚本摘要、hygiene来源和parser由同一个face构建。
- 镜像固定为原 `sha256:64472be326bc6cb14d3fb3beea3bd6ac8f71bab29c159c6e92538adcbe55c27f`，仅按正式replay派生镜像消费方式覆盖image身份字段，不变更材料。资源profile摘要 `sha256:3ec1bfa87ff800d5d2c5e53e874603f6850b64e1392baa167968b9ec31a50a94` 与原记录一致。
- spec预算原样保持env-reset300／apply120／test1800秒；grade deadline3600秒与正式replay默认相同，外层3900秒只是保护。没有安装／测试命令／奖励或参考变化。

这属于显式重评已持久化工件，使用新run标识关联旧物理attempt事实；没有伪称旧内存注册表仍存活，也没有启动新actor。

## 真实调用和失败收口

执行模式检查本run无人占用、固定镜像存在，调用一次正式 `manager.grade(workspace=None, frozen_delta=source)`。子类只记录phase后调用super，Docker包装只记录正式调用的argv/输入/输出；没有截获或替换census结果、baseline解析、摘要比较及异常。`_verify_baseline_rebuild`实际可达，未走legacy diff，也没有工具层重试或自动追加17071。

发生 `BaselineIntegrityError(reason_code="baseline_digest_mismatch")` 明确记录完整traceback、phase并以20退出；其他fatal/异常/意外报告各自非零。不会把预期反例的fatal转换为普通reward0。只有真实正式报告是unresolved/tests_failed/reward0才以0说明假说未复现。

finally记录manager时序/记录并以独立时限close，随后分别精确查询 `label=rh2.run_id=<本次独占run>` 的容器和网络。close失败、资源残留或查询失败均使退出码为24，保留原评分退出码。manager只清自有记录；startup没有共享标签扫除逻辑。新输出不能位于代码或原证据目录；执行结束后再次核原输入，防止本次探针静默改写证据。

## 后续读取范围

需独立读取实际 `status.json` 的异常和manager清理，并从 `docker_calls` 原始census输出重建摘要；缺report/测试日志要与失败phase一致。若只在baseline阶段fatal，不能写成测试失败，也不能把本工具结果作为修复完成。F1及既有成功子链见 [actor证据审查](d6_actor_evidence_review.md)。修复实现及新冻结版本另审。
