# MONAI 公开开发检查草案

2026-10-03。这些清单用于真实 actor 的公开开发检查，不包含 gold、私有测试补丁或错误候选。新机尚未运行；清单里的 base 预期只是需要核实的公开问题，不能当成已通过的证据。执行时只向 actor 提供清单中的公开命令，不挂载本工作包的材料／控制／评审目录。

- [2446 命令](monai2446_actor_commands.json)：复用已验公开清单，检查兼容 NiBabel、数组列表示例和原 SmartCache 模块。
- [3715 命令](monai3715_actor_commands.json)：检查 CPU／解释器／源码身份，分别真实运行非空的枚举和字符串 train/eval 示例，执行原公开模块。字符串失败必须核到 `unsupported mode`；枚举 train 示例应保留输入梯度。
- [6975 命令](monai6975_actor_commands.json)：复用既有公开清单，并补实际 NIfTI 文件和题面原 LoadImaged／RandAffined 示例。公开原例可执行性与确定性内存 Flip 检查分开验收。随机变换后的直调和 Dataset 图像不互比，原例仍需查看实际 lazy 日志。

预期工作区为 `/testbed`，解释器为 `/opt/miniconda3/envs/testbed/bin/python`。这些路径来自锁定镜像的既有材料；仍需核对新机真实 actor 的生效结果。正式调用使用共享维护者发布的不可变源码、prepared 及材料，不用本清单绕过登记。
