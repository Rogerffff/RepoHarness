"""固定两个 member 的 advantage，展示早期动作 mask 后的直接梯度缺口。

这是两阶段、参数分离的数学反例，不是神经网络训练复现。
第二阶段参数与 theta 无关；为聚焦动作覆盖省略共同的正分母。
"""

import json
import math


def objective(theta, train_first_action):
    probability = 1 / (1 + math.exp(-theta))
    first_stage = (
        0.5 * math.log(probability)
        - 0.5 * math.log(1 - probability)
    ) / 2
    return first_stage if train_first_action else 0.0


theta = 0.8
epsilon = 1e-5
gradients = {}
for keep in (True, False):
    derivative = (
        objective(theta + epsilon, keep) - objective(theta - epsilon, keep)
    ) / (2 * epsilon)
    gradients["保留早期动作" if keep else "屏蔽早期动作"] = derivative

assert abs(gradients["保留早期动作"] - 0.25) < 1e-8
assert gradients["屏蔽早期动作"] == 0
print(json.dumps({
    "scope": "固定采样组，最大化 advantage 加权 logprob；不是完整 GRPO 复现",
    "actions": [1, 0],
    "terminal_rewards": [1, 0],
    "advantages": [0.5, -0.5],
    "d_objective_d_theta": gradients,
}, ensure_ascii=False, indent=2))
