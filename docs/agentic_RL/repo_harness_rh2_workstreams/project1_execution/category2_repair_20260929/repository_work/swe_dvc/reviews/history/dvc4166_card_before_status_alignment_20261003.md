# DVC4166 当前题卡

2026-10-03。状态：**v2草案私有CPU诊断及非作者材料／原日志窄核已完成；公开actor交付已独立核实，正式评分和模型探针未完成**。题面不变。完整材料身份、参考前后清单与映射见 [revision.json](revision.json)。

公开目标：`.dvcignore` 的尾斜杠目录规则及否定匹配按文件/目录区别工作。题面的七种写法并不等价：`*`加`!scripts`仍会过滤子项，不强求七种都返回相同结果；`/*`加`!/scripts/`是已经核实的缺陷。pathspec版本会改变语义。

历史可复用：grader固定pathspec0.8.1/networkx2.3+rh2.1；actor_v1用pathspec0.8.1及与grader代码等价的networkx2.3 gcd兼容改动，ignore29项通过。初态setup.py预改不能记作候选业务修改。见 [09-29复核](../../../../../swegym40_status_20260929/reviews/dvc_conan_dask.md)及 [原题卡/独立核查](../../../../../swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch02/results/iterative__dvc-4166/review.md)。

本轮追加：尾斜杠必须剪枝非空目录（F2P）；同名普通文件仍可读取（P2P）；非scripts示例的否定目录能保留实际叶文件（F2P）。用tree可见性与内容断言，避免只枚举文件而漏掉“空目录其实仍可见”。候选只去掉正向规则末尾斜杠；它预计通过原目录排除F2P，却会错误隐藏同名普通文件。原正式分仍待运行，不称已证漏奖。

原两个前导空格case共享截断键。本草案只给这两条case显式ID，输入及断言不变；原P2P单键映射为两个精确节点，原59条参考展为60条，再追加3条。其它节点保留。私有collection已确认两个实际节点，正式绑定仍待维护者登记，**不通过修改全局parser补漏**。

初始矩阵预期noop0/gold1/去尾斜杠0。运行前核pathspec与networkx改动字节、原/有效节点映射及新宿主身份。若正对照或候选出现非参考失败，保留解释，不把仅reward值当完整验收。通过后由本线程提交与分析探针。

v1六次私有诊断见 [cpu_diagnostics_v2.json](cpu_diagnostics_v2.json)：原版63节点，gold和去尾斜杠全过；原截断键真实对应两条PASS，原58个P2P键展为59个节点。v1草案新增否定目录仅从该目录直接walk，base也过，未证明根目录可见性。旧v1完整材料存于 [history](history/dvc4166-behavior-v1-draft/revision.json)，旧诊断不改。

v2只加 `tree.isdir("kept")` 验否定目录恢复，原/新参考仍3F/60P，原输入/断言保留。定向重验见 [cpu_diagnostics_v3.json](cpu_diagnostics_v3.json)：66节点无缺席，noop三个F2P均失败、60个P2P均过；gold全过；去尾斜杠失败新否定目录F2P及新普通文件P2P。原版三方诊断可复用，新版仍不是正式reward。

[非作者v2窄核](../../reviews/non_author_4166_9395_v2_review_20261003.md) 已独立核对一条新断言、三个原日志、63个参考、66个执行节点及清理，无新增材料阻断；未验收正式评分、actor或资格。

四题依赖准备见 [CPU准备记录](../../cpu_preparation_20261003.json)。本题重建2.3+rh2.1使用E13确切gcd代码；新wheel SHA为 `1aae272f148313261e4c8b5fb15717d430cd1828371cd94ccd2f79de9f27c412`，不冒用旧wheel摘要。source worktree不变、pip check0。首准备的脚本变量误报与首诊断误要求pygit2均已修正，失败产物和清理记录保留；不混入业务候选结果。

[本轮公开actor检查](public_actor_r5_v2.json) 已完成真实CC/relay的四条公开命令，29个既有公开测试实际通过且无skip／缺失；首请求逐字交付题面和开发说明，身份/profile一致，自有容器与网络清理。完整原件已SHA校验回收到本机，[非作者运行原件读回](../../reviews/non_author_actor4166_9395_runtime_review_20261003.md)已完成，无新增阻断；正式CPU评分和模型探针尚未完成。
