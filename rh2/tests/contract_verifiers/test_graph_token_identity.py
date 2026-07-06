"""契约测试 1：Trace 消息图的 token identity 不变量（rh2 S0-2）。

rh2 依赖 verifiers v1 的三条图层行为（升级 verifiers 前必须重新验证）：

1. token drift 走 fork：同一段消息文本（message_hash 完全相同）在 token ids
   发生漂移（retokenization drift）时，`commit` 必须在分歧节点 fork 出新分支，
   而不是静默复用旧 token 前缀——否则训练样本的 token 出处（provenance）会被污染。
2. 分支拼接恒等式：沿一条 Branch 依次拼接每个节点的 `token_ids`，
   精确等于模型这一轮真实看到的 `prompt_ids + completion_ids`。
3. sampled / mask / logprobs 对齐：`mask=True` 只标模型采样出的 completion token；
   `logprobs` 与 mask=True 的 token 一一对应；prompt 里伪造的 assistant 消息
   `sampled=False`，不算模型轮次。

参照上游 tests/v1/test_graph.py 的用例结构自写最小版（pin: 5885ab9c）。
"""

import verifiers.v1 as vf
from verifiers.v1 import graph
from verifiers.v1.types import TurnTokens


def _response(
    message: vf.AssistantMessage, tokens: TurnTokens | None = None
) -> vf.Response:
    """构造一个最小 Response（不经过任何模型调用）。"""
    return vf.Response(
        id="",
        created=0,
        model="test",
        message=message,
        finish_reason="stop",
        tokens=tokens,
    )


def _commit_turn_one(trace: vf.Trace) -> None:
    """第一轮：user "u1" -> assistant "a1"。
    prompt_ids=[1,2,3]（user 占 [0,2)，[2,3) 是 generation prompt 脚手架），
    completion_ids=[4,5]，逐 token logprobs=[-0.5,-0.25]。"""
    graph.prepare_turn(trace, [vf.UserMessage(content="u1")]).commit(
        _response(
            vf.AssistantMessage(content="a1"),
            TurnTokens(
                prompt_ids=[1, 2, 3],
                completion_ids=[4, 5],
                completion_logprobs=[-0.5, -0.25],
                message_spans=[(0, 2)],
            ),
        )
    )


# ---------------------------------------------------------------------------
# 断言 1：token drift 必须 fork，不允许静默复用旧前缀
# ---------------------------------------------------------------------------


def test_token_drift_forks_instead_of_silently_reusing_prefix():
    user = vf.UserMessage(content="u1")
    a1 = vf.AssistantMessage(content="a1")
    u2 = vf.UserMessage(content="u2")

    def second_turn(trace: vf.Trace, prompt_ids: list[int]) -> None:
        graph.prepare_turn(trace, [user, a1, u2]).commit(
            _response(
                vf.AssistantMessage(content="a2"),
                TurnTokens(
                    prompt_ids=prompt_ids,
                    completion_ids=[8],
                    message_spans=[(0, 2), (2, 5), (5, 7)],
                ),
            )
        )

    # 前置检查：两轮 prompt 里的 a1 与第一轮采样出的 a1 message_hash 完全相同，
    # 即 message 层看不出任何差异——后面的 fork 只能由 token identity 触发。
    assert graph.message_hash(a1) == graph.message_hash(
        vf.AssistantMessage(content="a1")
    )

    # 对照组：第二轮 prompt_ids 与已存前缀逐 token 一致 -> 保持单分支线性。
    linear = vf.Trace(task=vf.Task(idx=0, prompt="x"))
    _commit_turn_one(linear)
    second_turn(linear, [1, 2, 3, 4, 5, 6, 7])
    assert linear.num_branches == 1
    assert linear.branches[0].token_ids == [1, 2, 3, 4, 5, 6, 7, 8]

    # 漂移组：assistant 的一个 token 被重新 tokenize（4 -> 99），
    # 必须在该节点 fork 成两个分支。
    broken = vf.Trace(task=vf.Task(idx=0, prompt="x"))
    _commit_turn_one(broken)
    second_turn(broken, [1, 2, 3, 99, 5, 6, 7])
    assert broken.num_branches == 2
    assert sorted(b.token_ids for b in broken.branches) == [
        [1, 2, 3, 4, 5],
        [1, 2, 3, 99, 5, 6, 7, 8],
    ]

    # 反污染检查：原来采样出的 assistant 节点保持原 token 不被改写；
    # 漂移后的 a1 以"输入消息"身份重新入图（sampled=False、mask 全 False），
    # 也就是说漂移 token 绝不会进入可训练区。
    a1_nodes = [
        n
        for n in broken.nodes
        if isinstance(n.message, vf.AssistantMessage) and n.message.content == "a1"
    ]
    assert len(a1_nodes) == 2
    sampled_node = next(n for n in a1_nodes if n.sampled)
    drifted_node = next(n for n in a1_nodes if not n.sampled)
    assert sampled_node.token_ids == [3, 4, 5]  # 原生成形态：gen prompt + completion
    assert drifted_node.token_ids == [3, 99, 5]  # 本轮真实看到的输入形态
    assert drifted_node.mask == [False, False, False]
    assert drifted_node.logprobs == []


# ---------------------------------------------------------------------------
# 断言 2：沿 branch 拼接 token_ids == prompt_ids + completion_ids
# ---------------------------------------------------------------------------


def test_branch_concat_equals_prompt_plus_completion_across_turns():
    trace = vf.Trace(task=vf.Task(idx=0, prompt="x"))
    _commit_turn_one(trace)

    # 第一轮后：唯一分支就是 turn1 的 prompt+completion。
    assert trace.num_branches == 1
    assert trace.branches[0].token_ids == [1, 2, 3] + [4, 5]

    # 第二轮：prompt 复述 [user, a1] 并追加 u2。
    # prompt_ids 前 5 个 token 与已存前缀逐 token 一致（[1,2,3,4,5]），
    # u2 占 [5,6)，[6,7) 是 generation prompt，completion=[8,9]。
    turn2_prompt = [1, 2, 3, 4, 5, 6, 7]
    turn2_completion = [8, 9]
    graph.prepare_turn(
        trace,
        [
            vf.UserMessage(content="u1"),
            vf.AssistantMessage(content="a1"),
            vf.UserMessage(content="u2"),
        ],
    ).commit(
        _response(
            vf.AssistantMessage(content="a2"),
            TurnTokens(
                prompt_ids=turn2_prompt,
                completion_ids=turn2_completion,
                completion_logprobs=[-1.0, -2.0],
                message_spans=[(0, 2), None, (5, 6)],
            ),
        )
    )

    assert trace.num_branches == 1  # 无漂移 -> 仍是单分支
    branch = trace.branches[0]
    # 核心恒等式：节点 token 拼接 == 最后一轮的 prompt_ids + completion_ids。
    assert branch.token_ids == turn2_prompt + turn2_completion
    # 节点粒度复核：每个节点存的是"自己新增的 token 增量"。
    assert [n.token_ids for n in branch.nodes] == [[1, 2], [3, 4, 5], [6], [7, 8, 9]]


# ---------------------------------------------------------------------------
# 断言 3：sampled / mask / logprobs 三者对齐
# ---------------------------------------------------------------------------


def test_mask_and_logprobs_align_with_sampled_tokens():
    trace = vf.Trace(task=vf.Task(idx=0, prompt="x"))
    _commit_turn_one(trace)

    user_node, assistant_node = trace.nodes
    # 输入消息节点：全部不可训练，无 logprobs。
    assert user_node.sampled is False
    assert user_node.mask == [False, False]
    assert user_node.logprobs == []
    # assistant 节点 = generation prompt 脚手架(False) + 采样 completion(True)。
    assert assistant_node.sampled is True
    assert assistant_node.mask == [False, True, True]
    # 节点级对齐：logprobs 长度 == mask 里 True 的个数。
    assert len(assistant_node.logprobs) == sum(assistant_node.mask) == 2
    assert assistant_node.logprobs == [-0.5, -0.25]

    # 分支级对齐：token_ids / sampled_mask / logprobs 三个序列等长；
    # logprobs 只在 mask=True 的位置有值（其余补 0.0），且顺序与采样顺序一致。
    branch = trace.branches[0]
    assert (
        len(branch.token_ids) == len(branch.sampled_mask) == len(branch.logprobs) == 5
    )
    assert branch.sampled_mask == [False, False, False, True, True]
    assert branch.logprobs == [0.0, 0.0, 0.0, -0.5, -0.25]
    assert [
        lp for lp, sampled in zip(branch.logprobs, branch.sampled_mask) if sampled
    ] == [-0.5, -0.25]


def test_prompt_supplied_assistant_message_is_not_a_sampled_turn():
    """prompt 里伪造的 assistant/tool 消息（few-shot、fabricated context）必须
    sampled=False：`sampled` 是"模型真的采样过"的出处标记，不能靠 role 判断。"""
    trace = vf.Trace(task=vf.Task(idx=0, prompt="few-shot"))
    fabricated = vf.AssistantMessage(
        content=None,
        tool_calls=[vf.ToolCall(id="call_0", name="lookup", arguments="{}")],
    )
    real = vf.AssistantMessage(content="real answer")

    graph.prepare_turn(
        trace,
        [
            vf.UserMessage(content="question"),
            fabricated,
            vf.ToolMessage(content="fabricated result", tool_call_id="call_0"),
        ],
    ).commit(_response(real))

    assert [n.sampled for n in trace.nodes] == [False, False, False, True]
    assert trace.num_turns == 1  # 只有真采样的那一轮计入 turn 数
    assert trace.assistant_messages == [real]
