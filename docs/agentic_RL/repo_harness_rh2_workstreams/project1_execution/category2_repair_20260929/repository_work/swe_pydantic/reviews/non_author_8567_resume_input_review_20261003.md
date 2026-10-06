# Pydantic 8567：七行补验输入的非作者静态窄核

2026-10-03。**静态核查通过，未发现新输入阻断。** 新输入唯一内容差是删除已核收的 noop／gold；后七行、其它题、release、材料、安装和镜像字段完全相同，runner 逐字节未变。此次没有核收共享 CPU 恢复或远端上传读回，没有运行补验。七行实际结果、公开 actor 和联合 CPU 验收仍缺，**全题 CPU／普通 GPU 探针未就绪，未授训练资格**。

审查者不是材料／runner／输入作者，已见私有上下文，不是 fresh 公开读者。复用[失败轮非作者意见](non_author_8567_partial_cpu_review_20261003.md)、[R14 固定入口意见](non_author_remaining_runner_review_20261003.md)及已有材料核查；只读本地文件，使用标准库深比较、SHA／大小复算及源码／AST 阅读，没有运行 helper、SSH、Docker、安装、项目测试或模型。只写本报告和[同名 JSON](non_author_8567_resume_input_review_20261003.json)。

## 固定输入的唯一变化

读取原 `remaining/formal_inputs.json`，深拷贝后仅令 `tasks.8567.candidates = 原列表[2:]`；该对象与[新 formal_inputs.json](../cpu_acceptance_20261003/8567_resume_v1/formal_inputs.json) **严格相等**。因此全部其它顶层字段、其它三题、8567 的参考节点／source／assets／安装／镜像，以及保留七行的 patch、源码 SHA、预期状态／分数逐字段相等。输入仍包含其它三题；实际补验必须选择 `--task 8567`，本题才执行这七行。

| 对象 | 字节数 | SHA256 |
| --- | ---: | --- |
| 原／新 runner | 22791，各自相同 | `b127f7309ffae3eae2bbe834c595f846104406e2f858b8073ff2182d0a2ce3c5` |
| 原固定输入 | 349851 | `bea70edd55d2a316b5d92fde1a3a894e9c79363a168e2cd92c7de2d40b83ac1b` |
| 新固定输入 | 333062 | `cce81e77a4122786ed78f8134d79fab11e7c46e4b851c80308c393076b3c3845` |
| resume_scope | 3684 | `4c8a18b57103d09a8d3d7e7c61f0d81a2d408f30372595aac5ecff879fdcb3b0` |
| upload_manifest | 1433 | `0675d9a60ac9ab5e8976352e3db81a161f17b0f94d98cb9e9e10916a1755e365` |

七行原顺序为 `c3_reorder/upstream261/ok_post_attach/bad_nonvalidators_after_pv/c3_serpass/rv_ser_to_end/n_python_only`，预期 `1/0/1/0/0/0/0`。这些只是原计划预期，尚非本轮实际评分。release 仍为 `cat2-cpu-r2e089092-swe34-dvc-pyd-20261003-v1`，manifest `51b833975be2c3354be45b731552235a33070315f0039c8e6f54987de95f6ca8`；revision 和私有材料未改。

## 旧结果归属与上传边界

[resume_scope.json](../cpu_acceptance_20261003/8567_resume_v1/resume_scope.json) 的两行复用均指向原 job `pyd8567-formal-20261003001737-r14-b631d`，原 reward 为 0。所绑定的旧 MD／JSON 大小与 SHA 均复算相等，并与其 `completed_rows_reusable`、实际逐行 reward 一致。旧 c3 的 `failed_old_c3_reward=null`、`old_failure_preserved=true` 与失败轮原意见一致；没有把 null 改成模型 0，也没有把旧两行移记到新 job。

[upload_manifest.json](../cpu_acceptance_20261003/8567_resume_v1/upload_manifest.json) 指定独立 namespace **`formal_8567_resume_v1`**，四个成员均为正常文件，无 symlink；成员路径、实际大小和 SHA 全部一致，远端成员名无绝对路径或 `..`：

| 远端相对成员 | 字节数 | SHA256 |
| --- | ---: | --- |
| `README.md` | 1588 | `b5fd087efb05814bd0aadcd02ad4bbe9435a7074d684610a4a7c49e7a2cf69ea` |
| `inputs/formal_inputs.json` | 333062 | `cce81e77a4122786ed78f8134d79fab11e7c46e4b851c80308c393076b3c3845` |
| `resume_scope.json` | 3684 | `4c8a18b57103d09a8d3d7e7c61f0d81a2d408f30372595aac5ecff879fdcb3b0` |
| `inputs/run_formal.py` | 22791 | `b127f7309ffae3eae2bbe834c595f846104406e2f858b8073ff2182d0a2ce3c5` |

这四件不含材料副本、共享控制修改或 helper；manifest 本体是本地成员索引，不是其自列成员。材料根仍规定为 `packages/swe_pydantic/formal_v2/materials`。runner 的 `--material-root` 是必填参数，按其值读取固定资产和 patch，不能从新 namespace 自动猜材料根；实际派发应明确传原材料根，输出置于新 namespace／新唯一 job。新旧 namespace 分离是本轮上传与派发约定，此时尚无实际远端 argv 或读回证据。runner 的 `out.mkdir(exist_ok=False)` 会拒绝覆盖已有作业输出；此次不改旧 formal_v2 输入或历史工件。

## 执行条件与 helper 范围

同字节 runner 仍设置候选／grader 2 CPU、4 GiB，既有保护脚本和 300 秒上限没有改动；scope 的 `resource_and_timeout_change=false/source_or_shared_control_change=false` 与此次实际差异相符。新的输入没有新增恢复诊断、保护绕过或自动重试机制。

[README](../cpu_acceptance_20261003/8567_resume_v1/README.md) 与 scope 一致：必须先读取并核收共享 CPU 诊断／恢复、取得本静态意见、完成新 namespace 逐件上传读回，然后由题主以新唯一 job 经全机 `cpu_slot` 派发。名额空闲不是恢复证据。此流程要求来自本轮父任务和已定协作范围，不是本报告新增审批条件；未在 runner 内实现自动恢复门控，派发方仍负责记录其满足情况。运行后两个 job 原件分别保留，另建联合验收清单，不把七行写回旧失败轮。

顺带阅读本地 `prepare_8567_resume_v1.py`，SHA `f5b1400d2cba806e19710ef0ac94474af57f62457149cbacc521f281bc613650`。其说明“生成一次性七行输入，不派发、不修改旧输入或原件”准确：只用标准库，先核原 runner／输入／旧意见及固定资产，深拷贝删除前两行，`dest.mkdir(exist_ok=False)` 防覆盖，生成四成员索引；无远端、Docker、安装或执行入口调用。它未验证共享 CPU 恢复或上传，也未运行新矩阵，因此不得把 helper 的断言／生成成功当作这些验收。helper 只是本地准备工具，不纳入新的公共标准或四成员上传范围。

本报告只确认**补验输入的身份和选择范围**。未核收远端恢复／上传，未执行七行或公开 actor，未形成联合完整 CPU 意见；baseline 环境锚 null、共享 parser 非参考参数名口径、typed 训练租约及既有语义边界仍按旧意见保留，未被本静态通过补齐。
