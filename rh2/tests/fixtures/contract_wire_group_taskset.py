"""EnvServer 契约测试用的最小 taskset 插件（带 @group_reward）。

用于验证 info() 的 requires_group_scoring 字段：taskset 定义了 @group_reward
时必须返回 True（训练调度器据此决定走 run_group 而不是 run_rollout）。
"""

import verifiers.v1 as vf

__all__ = ["ContractWireGroupTaskset"]


class ContractWireGroupTaskset(vf.Taskset[vf.Task, vf.TasksetConfig, vf.State]):
    def load_tasks(self) -> list[vf.Task]:
        return [vf.Task(idx=0, prompt="group smoke task")]

    @vf.group_reward
    async def all_zero(self, traces) -> list[float]:
        return [0.0 for _ in traces]
