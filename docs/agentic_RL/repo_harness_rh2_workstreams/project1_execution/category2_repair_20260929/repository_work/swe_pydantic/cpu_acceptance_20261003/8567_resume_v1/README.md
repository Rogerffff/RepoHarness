# 8567：保留两行原结果，仅补验七行

2026-10-03。本目录仅是新的补验输入，尚未远端执行。旧 R14 job 的 noop／gold 两行各 162 参考实际 0 分已获[非作者窄核](../../reviews/non_author_8567_partial_cpu_review_20261003.md)，保留原 job 归属和字节，不重跑。旧 c3 在保护控制面调用 0099 超时，安装／测试未开始；原 reward=null 和失败原件不改。

新输入只从旧 `tasks.8567.candidates` 去掉 noop／gold，按原顺序保留 c3_reorder、upstream261、ok_post_attach、bad_nonvalidators_after_pv、c3_serpass、rv_ser_to_end、n_python_only，预期 1／0／1／0／0／0／0 尚未实际观察。其它题输入、材料、公开输入、安装、精确镜像、资源和预算逐字段不变。[runner](run_formal.py)与旧文件逐字节相同；材料仍读取原已冻结的 formal_v2/materials，不复制或覆盖旧输入。独立[范围清单](resume_scope.json)绑定原 job、两行复用意见和新旧输入 SHA。

共享 CPU 支持 `swe-pydantic8567-control-protect-timeout-support-v1-20261003` 的诊断／恢复尚待核收。非作者新输入静态核查、实际上传读回和恢复核收完成后，才由题主用新唯一 job 经全机作业槽执行。不得禁用保护、提高300秒上限、绕过作业槽或因名额空闲自动重试。

补验后保留两个独立 job 的原件，另建联合验收清单；不得将七行结果写入旧失败轮，也不得据此跳过公开 actor 和全题非作者验收。现在不能提交本题 GPU 探针或授予训练资格。
