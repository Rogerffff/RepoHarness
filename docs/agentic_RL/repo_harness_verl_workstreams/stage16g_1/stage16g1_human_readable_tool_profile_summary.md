# Stage 16G.1 Tool Profile Summary

本摘要只包含 public-safe 计数和结论，不包含本机绝对路径、私有 artifact 或 raw patch。

- registry record count: 27
- blocking capability count: 17
- post 16G optional count: 4
- inspection status: passed

## Owner Stage Counts

- 16G.2: 5
- 16G.3: 4
- 16G.4: 9
- 16G.5: 2
- not_required: 3
- post_16G_optional: 4

## Gate Summary

- `swe_public_core` 不包含 persistent diagnostic shell。
- `run_episode` 是主入口，旧 `run_task` 只作为 legacy compatibility。
- 单个工具事件不是 policy loss sample；训练资格在 trajectory / sample 层判断。
