"""契约测试 3：EnvServer/EnvClient wire 协议（rh2 S0-2）。

rh2 长期把"训练框架 <-> 环境服务"的边界压在 verifiers 的 EnvServer/EnvClient 上，
因此固定两层行为：

1. wire 类型（serve/types.py）的 msgpack 往返字段不丢：
   - 请求按 EnvClient 的路径打包：msgpack.packb(req.model_dump(mode="json"))，
     `method` 是 ClassVar、不进 payload（作为独立 ZMQ 帧路由）。
   - 响应按 EnvServer 的路径打包：msgpack.packb(resp.model_dump(mode="python"),
     default=msgpack_encoder)；Trace 的 token_ids/mask/logprobs/reward/info 等
     训练关心的字段必须原样穿越，transient `state` 不上线。
2. in-proc 起 EnvServer + EnvClient（真实 ZMQ localhost socket）：
   health / info 往返可用；info 返回 num_tasks 与 requires_group_scoring
   （requires_group_scoring == taskset 是否定义 @group_reward）。

不依赖网络模型 API、不依赖 docker：不发起任何 run_rollout（那需要模型端点，
归 S0-3/S0-5 验证）；taskset 是 tests/fixtures/ 下的本地插件模块。
"""

import asyncio
import contextlib
import sys
from pathlib import Path

import msgpack
import verifiers.v1 as vf
from verifiers.utils.serve_utils import msgpack_encoder
from verifiers.v1.clients.config import TrainClientConfig
from verifiers.v1.env import EnvConfig
from verifiers.v1.graph import MessageNode
from verifiers.v1.serve.client import EnvClient
from verifiers.v1.serve.server import EnvServer
from verifiers.v1.serve.types import (
    BaseResponse,
    InfoResponse,
    RunGroupRequest,
    RunGroupResponse,
    RunRolloutRequest,
    RunRolloutResponse,
)
from verifiers.v1.types import AssistantMessage, SamplingConfig, Usage, UserMessage

# taskset 插件通过模块名解析（loaders._import_plugin），把 fixtures 目录挂上
# sys.path 后，taskset.id="contract_wire_taskset" 就能被 EnvServer 导入。
_FIXTURES_DIR = str(Path(__file__).resolve().parents[1] / "fixtures")
if _FIXTURES_DIR not in sys.path:
    sys.path.insert(0, _FIXTURES_DIR)


class WireSmokeTask(vf.Task):
    """带 taskset 自有字段的任务：验证 WireTask 在客户端吸收未知字段。"""

    answer: str = ""


def _client_pack(req) -> bytes:
    """复刻 EnvClient._request 的打包方式。"""
    return msgpack.packb(req.model_dump(mode="json"), use_bin_type=True)


def _server_pack(resp) -> bytes:
    """复刻 EnvServer._handle 的打包方式。"""
    return msgpack.packb(
        resp.model_dump(mode="python"), default=msgpack_encoder, use_bin_type=True
    )


def _unpack(data: bytes):
    return msgpack.unpackb(data, raw=False)


# ---------------------------------------------------------------------------
# wire 类型 msgpack 往返：请求侧
# ---------------------------------------------------------------------------


def test_run_rollout_request_msgpack_roundtrip_preserves_fields():
    req = RunRolloutRequest(
        task_idx=3,
        client=TrainClientConfig(
            base_url="http://127.0.0.1:9/v1",
            api_key_var="RH2_TEST_KEY",
            pool_size=2,
        ),
        model="qwen/test-model",
        sampling=SamplingConfig(temperature=0.7, top_p=0.95, max_tokens=64, seed=1234),
    )
    payload = req.model_dump(mode="json")
    # method 是 ClassVar：不进 payload，作为独立 ZMQ 帧路由。
    assert "method" not in payload
    assert RunRolloutRequest.method == "run_rollout"

    restored = RunRolloutRequest.model_validate(_unpack(_client_pack(req)))
    assert restored == req  # pydantic 按字段比较：所有字段无损往返
    # 判别式 union 正确收窄回 TrainClientConfig（train 特有字段不丢）。
    assert restored.client.type == "train"
    assert restored.client.pool_size == 2
    assert restored.client.base_url == "http://127.0.0.1:9/v1"
    # SamplingConfig extra="allow"：透传字段（如 seed）也要无损。
    assert restored.sampling.model_extra == {"seed": 1234}
    assert restored.sampling.max_tokens == 64


def test_run_group_request_msgpack_roundtrip_preserves_n():
    req = RunGroupRequest(
        task_idx=1,
        n=8,
        client=TrainClientConfig(
            base_url="http://127.0.0.1:9/v1", api_key_var="RH2_TEST_KEY"
        ),
        model="m",
        sampling=SamplingConfig(),
    )
    assert RunGroupRequest.method == "run_group"
    restored = RunGroupRequest.model_validate(_unpack(_client_pack(req)))
    assert restored == req
    assert restored.n == 8


# ---------------------------------------------------------------------------
# wire 类型 msgpack 往返：响应侧（Trace 字段不丢）
# ---------------------------------------------------------------------------


def _training_trace() -> vf.Trace:
    """构造一条带训练关键字段的最小 Trace（user + 采样 assistant 两个节点）。"""
    tr = vf.Trace[WireSmokeTask, vf.State](
        task=WireSmokeTask(idx=0, prompt="q", answer="gold"),
        nodes=[
            MessageNode(
                parent=None,
                message=UserMessage(content="q"),
                token_ids=[1, 2],
                mask=[False, False],
            ),
            MessageNode(
                parent=0,
                message=AssistantMessage(content="a"),
                sampled=True,
                token_ids=[3, 4, 5],
                mask=[False, True, True],
                logprobs=[-0.5, -0.25],
                finish_reason="stop",
                usage=Usage(prompt_tokens=2, completion_tokens=2),
            ),
        ],
    )
    tr.record_reward("verifier", 0.5)
    tr.info = {"artifact": "logs/build.txt"}
    tr.stop("agent_completed")
    return tr


def test_run_rollout_response_trace_survives_msgpack_roundtrip():
    tr = _training_trace()
    # 复刻 EnvServer._run_rollout：信任的 trace 直接 model_construct 进响应。
    resp = RunRolloutResponse.model_construct(trace=tr)
    wire = resp.model_dump(mode="python")
    # transient state 不上线（升级时若 state 开始被序列化，是行为变化）。
    assert "state" not in wire["trace"]

    restored = RunRolloutResponse.model_validate(_unpack(_server_pack(resp)))
    assert restored.success is True
    rt = restored.trace
    assert rt is not None
    # 客户端拿到 Trace[WireTask]：taskset 自有字段进 model_extra，不需要导入 taskset。
    assert rt.task.model_extra == {"answer": "gold"}
    assert rt.task.idx == 0 and rt.task.prompt == "q"
    # 训练关心的 token 级字段逐一无损。
    assert rt.id == tr.id
    assert [n.token_ids for n in rt.nodes] == [[1, 2], [3, 4, 5]]
    assert rt.nodes[1].mask == [False, True, True]
    assert rt.nodes[1].logprobs == [-0.5, -0.25]
    assert rt.nodes[1].sampled is True
    assert rt.nodes[1].finish_reason == "stop"
    assert rt.nodes[1].usage is not None
    assert rt.nodes[1].usage.prompt_tokens == 2
    # 图结构与派生量在对端重算后一致。
    assert rt.num_branches == 1 and rt.num_turns == 1
    assert rt.branches[0].token_ids == [1, 2, 3, 4, 5]
    # 评分与元数据字段。
    assert rt.rewards == {"verifier": 0.5} and rt.reward == 0.5
    assert rt.stop_condition == "agent_completed"
    assert rt.is_completed is True
    assert rt.info == {"artifact": "logs/build.txt"}


def test_run_group_response_and_error_response_roundtrip():
    tr = _training_trace()
    group = RunGroupResponse.model_construct(traces=[tr, tr])
    restored = RunGroupResponse.model_validate(_unpack(_server_pack(group)))
    assert restored.traces is not None and len(restored.traces) == 2
    assert all(t.reward == 0.5 for t in restored.traces)

    # 失败响应是数据不是 crash：success/error 字段无损往返。
    err = BaseResponse(success=False, error="IndexError: boom")
    restored_err = BaseResponse.model_validate(_unpack(_server_pack(err)))
    assert restored_err.success is False
    assert restored_err.error == "IndexError: boom"


# ---------------------------------------------------------------------------
# in-proc EnvServer + EnvClient：health / info 往返
# ---------------------------------------------------------------------------


async def _serve_and_query_info(taskset_id: str) -> InfoResponse:
    """起一个 in-proc EnvServer（OS 分配端口），用 EnvClient 打 health+info。"""
    server = EnvServer(
        EnvConfig(taskset={"id": taskset_id}), address="tcp://127.0.0.1:0"
    )
    # `:0` 绑定后必须解析出真实端口（prime-rl 的子进程启动路径依赖这一点）。
    assert server.address.startswith("tcp://127.0.0.1:")
    assert not server.address.endswith(":0")
    server_task = asyncio.create_task(server.run())
    client = EnvClient(server.address)
    try:
        await client.wait_for_server_startup(timeout=30)
        assert await client.health() is True
        info = await client.info()
        assert info.success is True
        return info
    finally:
        await client.close()
        server_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await server_task


async def test_envserver_health_info_roundtrip_in_proc():
    info = await _serve_and_query_info("contract_wire_taskset")
    assert info.num_tasks == 3
    # 没有 @group_reward -> 调度器可以逐条 run_rollout。
    assert info.requires_group_scoring is False


async def test_envserver_info_reports_group_scoring():
    info = await _serve_and_query_info("contract_wire_group_taskset")
    assert info.num_tasks == 1
    # 定义了 @group_reward -> 调度器必须走 run_group。
    assert info.requires_group_scoring is True
