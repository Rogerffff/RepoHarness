# Dask7656 原环境 actor 核验

2026-09-29。`actor_original_v1` 已完成公开开发校准：真正的 UID54321/Claude Code2.1.205 执行4条命令，原例按目标路径失败，3条现有公开测试通过，收尾无残留。这证明未修问题可在实际 actor 下复现，尚不证明修复、正式评分或训练资格。

- 初态与导入：HEAD `07d5ad0ab1bc8903554b37453f02cc8024460f2a`，git status 为空；Python3.9.19 `/opt/miniconda3/envs/testbed/bin/python`，Dask 从 `/testbed/dask/__init__.py` 导入。
- 原例及增强例：均在 delayed.py:112 读取缺失 primary_key 时 AttributeError，RC1。增强例在第一条默认 Entry 就中止，**嵌套求值尚未执行**，不能算嵌套行为验证通过。
- 公开测试：test_to_task_dask、test_delayed_with_dataclass、test_traverse_false 全通过，3 passed / 49 deselected，pytest8.3.2，0.57秒。没有收集错误或私有测试注入。
- 正式装配：prelaunch / activation 均 ok；UID/GID54321，工作区可写，/rh2/bash_env 可读不可写且 root:0644；外网/直连上游被拒绝，relay 可达。配置2CPU/4GiB，prelaunch也读到相应cgroup值；8GiB writable quota仅声明，本记录不额外认证存储限额。
- 轨迹与清理：4次 Bash/4个结果，5个stub请求与5个message_start一致，result成功，stderr0字节；各capture284/670/670/1237字节均未截断；容器rm0、network/relay failures空、无标签残留，agent进程0。测试写了缓存，git状态仍空；不宣称未写文件。

`checks.interpreter_in_tool_result=false` 与 `bashenv_denied_for_agent=false` 是继承固定标记检查：父脚本查 RH2_SYS_EXECUTABLE/RH2_BASHENV_WRITE，而本题命令打印 PYTHON 且未发写入尝试。前者已由完整tool结果与activation实测解释；后者由prelaunch的ACTIVATION_WRITE=DENIED支持，未伪装为本题新增攻击测试。

初始 image inspect 在自动拉取前失败（RC1、空字段）；运行容器 image ID 实测为 `sha256:3e57a70d57e3691a4f53908d694b7e4a78055ef05a176ef63a5853bd56514d72`，但本attempt未保存RepoDigests，需root镜像清单补齐。原actor未记录pandas版本或distutils变量，不能冒称已对齐compat_v2b。实际CC收到的是Devcheck指令和预设公开命令，没有完整题面交付验收，也没有自主模型推理。

总起止48秒，solve12.552秒；逐命令墙钟未记录。stub返回的token/金额为合成字段，不计真实模型费用。完整来源及SHA见 `actor_original_result.json`，原件在 `runs/swegym_cpu_preprobe_20260929/remote/results/dask__dask-7656/actor_original_v1/`。

仍需：依赖对齐后必要复验、base/gold及退化语义/正式评分、完整参考与额外失败解释、输出投影/加载/清理、冷恢复及独立复核。
