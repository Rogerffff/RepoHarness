# Moto6114：两项既有 Neptune 名称回退的 CPU 原件读回

2026-10-03。作者读回已确认两处模型回归，独立运行结果审查待完成。这是两容器的代码行为诊断，不是新 37 参考的正式评分；没有修改旧 GPU raw1、FrozenPatch、旧 R7 或私有参考。

原 base 与实际 Qwen 候选内容分别在新容器运行相同两项名称调用。原代码 start 返回同名称的 started 对象，cluster 仍存在；delete 返回同名称对象且移除 cluster。候选 start 抛出 InvalidDBClusterStateFault，delete 抛出缺少 deletion_protection 的 AttributeError，二者均保留原 cluster。原 Neptune 模块字节未改。

| 调用 | 原 base | 实际 Qwen 内容 |
| --- | --- | --- |
| RDS façade 按已有 Neptune 名称 start | 返回 started，名称正确，仍存在 | InvalidDBClusterStateFault，仍存在 |
| RDS façade 按已有 Neptune 名称 delete | 返回名称正确，已移除 | AttributeError，仍存在 |

job `moto6114-neptune-2a7e2a72a7c6` 的正式 slot 子进程从 00:48:11 到 00:49:47 UTC，退出 0；原 stdout 与 result 均为 two_original_name_delegation_regressions_confirmed。两项 probe 分别退出 0 表示观察结果已完整返回，不表示候选行为通过。raw_reward 均为 null，没有调用 grader 或模型。

使用固定 R7 prepared 绑定，公开 base `f01709f9ba656e7cf4399bcd1a0a07fd134b0aec`。实际 CPU 镜像为 `sha256:1d8dded2ee5bbe9275514fdc603116ac9f36da5e30c19b2d4ffcba4d4a9f27d5`；源 manifest 为 `cb35f7e131f8e46c8a6865e8fb618c09032ce5ee27f1122f79010a7cfae8ef9a`，源实际 ID 为 `fefec492f58ed0f8385a7e72234d296bd84d295031ce7e019f63fc33973ec249`。源 13 层为 derived 14 层的完整前缀。两臂均先验证原 RDS/Neptune 源字节，随后仅候选臂写入实际 FrozenPatch 唯一源码 entry 的完整解码内容，SHA 为 `05e9b6a1d3f57caaeba1a616fa3a1a9529ffa6f6aa6d91be9a5963a239b5171d`；实际 probe 又复核模块路径与这个 SHA。

实际 Docker inspect 与运行 argv、模块内观察分别证实 network none、2CPU／4GiB／PID512／shm64MiB、no-new-privileges、UID/GID54321、/testbed 的 testbed Python。两臂原 sanitize、trusted init、activation 均成功；每臂自身容器 rm0，容器和网络 label 查询都为空。26 条 Docker 调用均退出 0，stderr 为空。原 source 和候选观察均在 finally 清理前写出；job0、清理调用和终态查询分别已读，不能只用 result 摘要代替清理证据。

本次 CPU actual 镜像与旧 GPU 实际 `43f685…6e20` 不同。因此这是相同公开源码与实际候选代码内容的行为对照，不能称为原 GPU FrozenPatch 的重新评分，也不能直接给旧 raw1 改判。批准的新版保留题面/base/原 1F34P/ARN identity/预算，仅新增这两项既有行为 P2P。仍须发布新材料身份，并按新 1F36P 运行 noop／gold／wrong_first／实际 Qwen 对照及独立验收。

原件位置：`runs/category2_repair_20260929/moto_cpu_20261003/moto6114-neptune-2a7e2a72a7c6_evidence`。归档 SHA `166fd611c6c69a22d1a4e340e11091d179a550d95aba6b766a3d6a8aff8ce0d7`，transport manifest SHA `4612e200abad0b97074d48fe1a56ca14333f0f9d51a54da6f1c7f07944e66120`；9 件运行原件 SHA 和长度逐项吻合，原件未改。

| 原件 | 字节 | SHA256 |
| --- | ---: | --- |
| `job/status.json` | 797 | `3f9b1c8cd81236f7e2682fd86e8723d8ff538d19e189d0e282b3dacb731377ae` |
| `job/stderr.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `job/stdout.log` | 108 | `0075c4bfd2209c3b853acc3ff5b4b84fcfc6738a755f6abb3dbf5df34f2761b6` |
| `output/base.json` | 2938 | `21b214dffea8db4e6a44d6d914aa9195e03b4ec5cad87fcfc5b35610d86de8b8` |
| `output/candidate.json` | 3276 | `8e3918cd14786e7b400d33d858889a0cfc685f4647942b0789feba37a1e2e4da` |
| `output/docker_calls.json` | 75306 | `03379d1e832197f113a3d1bc03976b76275d6e89d3e72a3f4ddaeb181f78446a` |
| `output/image_inspect.json` | 8136 | `ceacbff8df010be40ae5cd78a2bf1e3f5ceca9111739faa250a17f6d77469656` |
| `output/observations.json` | 7330 | `7fc04735b6df83a96738b1fbd48012f8d219d777f8bc8f798f2152792599a04a` |
| `output/result.json` | 272 | `2dc4ee47db1dc5ef474daa1bcff389825b097afb3c58850c5bb81c34d14d7a3a` |
