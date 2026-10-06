# DVC 新自有 formal CPU 薄封装：限定离线核查（2026-10-03）

当前结论：应使用新增 `formal_cpu_check_v2.py`，未发现其受影响差异存在静态阻断。v2 已补足 v1 的 prepared 来源绑定：run 必须核对成功 prepare completion 的固定 SHA、同题目／release／runner／runtime 及 summary 三方一致，同时重核 prepared 文件身份链。官方调用、候选隔离和 R7／R8／R9 的 5839 拒跑未改变。以下保留 v1 观察，并补 v2 差异；manifest 的声明集合边界仍需保留。没有新 release／实际输入或 CPU／分数，不能授予运行或评分资格。

## 范围及实际身份

第一轮仅阅读 v1 与历史 runner，补核只新增读取 v2 入口；用 stdlib AST 解析和内存 `compile` 检查语法，没有执行其代码、subprocess、pytest、SSH、Docker 或正式 CPU，没有创建运行输入、修改入口或重核此前四题私有材料／actor。核查者已接触过私有上下文，不是 fresh 公开读者。

| 文件 | 本次实际 SHA256 |
|---|---|
| `formal_cpu_check.py`（v1，未改） | `ff048865c5d776f7d6ca70326e6e1ecb480ae0c1b344ec51a5fc8495f1dc5d6b` |
| `formal_cpu_check_v2.py`（当前应使用） | `16a78e7019827e126d0788dcbb4bf13bd0ce913a9df842b79b9c110e75dc24c0` |
| `runs/category2_repair_20260929/repository_work/swe_dvc/formal5839_r7_runner.py` | `4becb55d4c51c2550a51c267d2f6c858786b11deec4f9660f7ffa409e42622c3` |

新文件 SHA 与委派 pin 完全匹配；旧文件仅用来比较历史调用形式，不重新认可该旧 release 的运行结果。

## v1 已核行为（保留原观察）

- **固定 release 与成员校验（43–64 行）**：题目限定为 4166／5839／6954／9395，job 标签只允许字母数字、`_`、`-` 并要求题目前缀；release 标签同样不能注入路径。从固定 ROOT 下选 `releases/<release_id>/repo`，先核外部 manifest 的完整 SHA，再核声明 release ID；遍历所有 `files` 成员，检查 resolve 后仍在 repo 内、字节长度与完整 SHA。最后检查封装本身 SHA。这里的“固定”来自配置 pin，代码没有另设新 release 的全局白名单。
- **5839 旧版拒跑（14–18、47–48 行）**：R7 `cat2-cpu-r2e088-swe12-git-20261003-v1`、R8 `cat2-cpu-r2e088-swe13-git-20261003-v1`、R9 `cat2-cpu-r2e089092-swe13-git-20261003-v1` 均在 manifest 读取、job 创建及任何 subprocess 前抛异常；两种 mode 都受保护。其它三题不受该题专属拒跑影响。
- **不覆盖 prepare（65–81 行）**：series／job 使用合法标签，job 目录 `exist_ok=False`；prepare 发现 series 下已有 prepared 或 private 就拒绝，也不允许 candidate。输出位置在该 series 下，任务选择传 `swe_gym_lite::<instance_id>`。封装不复制或修改旧 prepared，也不改 grading revision。
- **候选与输出隔离（83–105 行）**：run 必须按配置候选键取值。非空 patch 路径 resolve 后必须位于 series base 内且 SHA 完全一致，传给官方入口的是该实际文件的 `patch:<path>`，没有重写 patch 字节；无文件只允许显式 `noop` 且 SHA 为 empty bytes。先核 prepared summary SHA、实际 Docker image ID，再将 eval_logs／artifacts／ledger 分配到独立新 job 目录。未给 `--candidate` 会 KeyError 失败，不会静默落到 noop；这是调用条件，不是成功误报。
- **正式入口未改（68–74、99–128 行）**：只用 stdlib；没有导入或实现 grader、节点绑定、reward、补丁应用、材料注册、评分解析或消费器改写。实际调用为当前 Python 加 `-B <selected release>/rh2/scripts/replay_grade.py <mode>`。另有一次只读 `docker image inspect` 前检，因此“仅调用官方入口”应理解为评分执行只委托该入口，而非完全没有其它 subprocess。
- **参数和记录**：prepare／run 的官方 CLI 参数均已出现在历史 runner；新增 `--input`、`--mode` 是封装自身参数。run 的题目 ID 形式、repeat=1、candidate-stage=900、grading-deadline=3600、cleanup=120、image-pull=1800、derived-image／recipe、日志与 ledger 选项保持历史调用形式。profile 环境明确设置 actor／grader 2 CPU、4 GiB、PID512，grader UID54322，run ID 独立；继承其它环境变量的行为也与历史 runner 相同。process.log 收集 stdout／stderr，completion 记录官方入口真实退出与日志／ledger SHA，main 返回该真实 rc；不从 ledger 伪造通过分数。`formal_entry_unchanged=True` 是封装声明，不等于实际运行验收。

## v1 条件性非阻断项（保留；第 1 项由 v2 处理）

**1. run 未自行保证 prepared 与所选 release／题目关联（83–85、99–100 行）。** prepare 的已有输出拒绝不等于 run 的版本绑定。若配置把旧 summary 的 SHA 填入 `prepared_summary_sha256`，并选择已有旧 prepared 的 series，封装自己的 SHA guard 会通过并把这个 summary 交给所选 release。它既没有重新 prepare，也没有改写旧 summary；但仅凭封装不能宣称已排除“旧 prepared 交给新 release”或“series 与当前题目不符”。官方入口是否另行拒绝须由对应 release 代码／输入验证，本轮没有扩大读取范围。新输入应体现独立 series 和该 release 新 prepare 得到的 summary pin；若需要封装自身提供这项保证，需显式关联校验。当前没有新输入，不能据此要求历史矩阵重跑或断言新作业已失败。

**2. manifest 校验以配置 pin 的声明集合为信任边界（52–62、74 行）。** 代码确实核对全部声明成员，但不检查 `files` 非空，不检查 `rh2/scripts/replay_grade.py` 或关键消费器一定在集合内，也不拒绝 repo 中未列出的额外文件。例如一个缺少官方入口条目的、但被配置 pin 接纳的 manifest，不会在封装层阻止调用该未列入检查的入口。没有新 manifest，不能认定实际交付清单有遗漏；“全成员已核”不能被放大成对整个 repo 及所有可能 import 文件的完整性保证。后续固定 manifest 本身应覆盖官方入口与拟调用的代码集合。

另一个可见但不阻断正常调用的记录限制：job 目录在 mode／candidate／prepared／image 前检完成前已创建（66–67 行）；这些前检失败会保留空 job 目录而没有 invocation／completion，同一 job ID 不能重用。调用方仍应保存原始进程 stderr／退出，避免将这种自有 guard 失败记作题目或模型失败。

## v2 受影响差异补核

v2 实际 SHA 与新 pin 一致，v1 文件 SHA 保持不变。离线 unified diff 仅见三个新增区域：`prepared_identity` 函数、run 的 prepare provenance／summary 绑定、成功 prepare 的 completion summary SHA 记录。AST／内存 compile 通过，没有执行代码；imports、官方 prepare／run 参数、profile 环境、release 全成员校验、候选字节、job 输出路径、5839 拒跑及真实 rc 返回均未变。

- **prepared 身份链（v2 35–55 行）**：summary.task_ids 必须恰为当前单题 `swe_gym_lite::<instance_id>`；prepared_dir／private_dir resolve 后必须等于本 series 两个目录；prepared manifest 实际 SHA 必须等于 summary pin。manifest 必须 task_count=1、tasks 长度=1，task_id 与 instance_id 均与本题精确匹配。每个声明 prepared 文件必须仍在 prepared 目录内且字节 SHA 一致；实际 private/host_grading_views.jsonl SHA、summary host SHA 和 manifest host SHA 三方一致。函数返回实际 summary SHA，没有重新定义 grading 内容或安装行为。
- **成功 prepare provenance（149–153 行）**：只有官方 prepare 返回 rc=0 后才调用上述身份链，把实际 summary SHA 写入 completion。若官方 prepare rc 非零，completion 仍记录真实非零 rc；若其返回 0 而身份链不符，则封装抛异常，不会生成可被 run 当成成功的 completion。
- **run 强绑定（106–115 行）**：从同 series 内配置指定 prepare_job_id 的 completion 读回，首先核 `prepare_completion_sha256`。随后要求 mode=prepare、process_exit_code=0、同 instance_id、release_id、release manifest SHA、runner SHA 与 runtime Python；再调用 prepared_identity，要求实际 summary SHA 与运行配置、固定 successful prepare completion 中的 SHA 三方相同。检查发生在 Docker inspect 和正式 run subprocess 前。

因此，v1 第 1 项所述“只凭旧 summary SHA 便交给新 release”的路径已由 v2 拒绝：旧 release／旧 runner completion 与当前配置不符；其它题目、别的 series 目录或被替换的 prepared／private 字节也会拒绝。输入仍是外部受信配置，未声称防御人为伪造 completion 和相应全部 pin。v1 第 2 项的 release manifest 必要成员覆盖及前检失败留空 job 目录观察仍适用于 v2，均没有新实际输入证明触发，当前不列为实际作业阻断。

当前执行应明确采用 v2、自身 v2 runner SHA 和新 prepare 产生的 completion SHA／summary SHA，不沿用 v1 的 completion。尚无实际配置和完成记录，本轮仅确认新增关联检查的静态控制流与字节链，没有宣布 prepared 已产出或运行已通过。该补核不涉及已完成的 actor 事实，也不要求历史重跑。

## 未验证及用途

没有新 release、运行配置、manifest 内容、候选文件、prepared 或真实 CPU／分数，所以未验证这些实际字节身份、官方新版本 parser、评分语义、镜像 profile 强制生效、cleanup 或最终 ledger。这次语法及参数形式比较只能支持薄封装静态审查；不能替代固定输入、官方入口运行与原件读回，不授予正式 RH2 reward、actor、环境／训练资格或模型探针通过。不修改共享入口，不要求旧四题矩阵重跑。
