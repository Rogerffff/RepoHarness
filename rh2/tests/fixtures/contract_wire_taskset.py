"""EnvServer 契约测试用的最小 taskset 插件（无 @group_reward）。

verifiers 的插件协议：模块通过 `__all__` 导出恰好一个 Taskset 子类，
taskset id（"contract_wire_taskset"）即模块名，测试通过 sys.path 使其可导入。
"""

import verifiers.v1 as vf

__all__ = ["ContractWireTaskset"]


class ContractWireTaskset(vf.Taskset[vf.Task, vf.TasksetConfig, vf.State]):
    """3 个占位任务，只用于让 EnvServer 的 info() 返回 num_tasks=3。"""

    def load_tasks(self) -> list[vf.Task]:
        return [vf.Task(idx=i, prompt=f"wire smoke task {i}") for i in range(3)]
