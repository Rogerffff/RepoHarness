"""契约测试 4：TrainClient 的 token-in/token-out 协议（rh2 S0-2）。

用本地 aiohttp 假引擎记录请求，固定 rh2 依赖的纯协议层行为（真实 vLLM 端点
验证归 S0-5，本测试不需要 GPU、不需要网络模型 API）：

1. 请求走 token-in：TrainClient 把消息交给 renderer 得到 prompt token ids，
   POST 到 `{base}/inference/v1/generate`（挂在服务根，不在 /v1 下），请求体带
   `token_ids`（而不是 `messages` 文本），sampling_params 强制带 renderer 的
   `stop_token_ids` 与 `logprobs=1`，session_id 通过 X-Session-ID 头透传。
2. 响应解析 token-out：Response.tokens 携带 prompt_ids + completion_ids +
   逐 token completion_logprobs（长度与 completion_ids 对齐）；assistant 消息
   内容来自对 completion token ids 的 parse_response；raw 里回填 chat.completion
   兼容响应给 harness 程序。
3. 与 Trace 图闭环：把 TrainClient 的 Response commit 进图后，分支 token 拼接
   精确等于 prompt_ids + completion_ids，logprobs 落在采样位。

renderer 选择说明：真实 renderer pool 初始化要按模型名下载 HF tokenizer，会引入
网络与缓存依赖；为保证离线可重复，这里用确定性 FakeRenderer 覆写 TrainClient
的私有钩子 `_renderer_pool`（TrainClient 没有公开的 renderer 注入口）。
升级 verifiers 时若该钩子改名/改签名，本测试会立即失败提示适配。
"""

from dataclasses import dataclass, field

from aiohttp import web
from openai import AsyncOpenAI

import verifiers.v1 as vf
from renderers.base import ParsedResponse, RenderedTokens
from verifiers.v1 import graph
from verifiers.v1.clients.client import SESSION_ID_HEADER
from verifiers.v1.clients.train import TrainClient
from verifiers.v1.dialects import ChatDialect

# FakeRenderer 的确定性方案：第 i 条消息渲染成 [100*(i+1), 100*(i+1)+1]，
# generation prompt 固定 [900, 901]。单条 user 消息的 prompt ids 即：
_EXPECTED_PROMPT_IDS = [100, 101, 900, 901]
_STOP_TOKEN_IDS = [7]
_COMPLETION_IDS = [201, 202, 203]
_COMPLETION_LOGPROBS = [-0.1, -0.25, -0.5]


class FakeRenderer:
    """确定性假 renderer：实现 TrainClient 用到的 Renderer 协议子集，
    不下载任何 tokenizer。非 RendererPool，因此 renderers.client 会内联执行。"""

    supports_tools = True

    def render(self, messages, tools=None, add_generation_prompt=False):
        token_ids: list[int] = []
        indices: list[int] = []
        roles: list[str] = []
        for i, message in enumerate(messages):
            roles.append(message["role"])
            token_ids += [100 * (i + 1), 100 * (i + 1) + 1]
            indices += [i, i]
        if add_generation_prompt:
            token_ids += [900, 901]
            indices += [-1, -1]  # 生成提示是脚手架，不归属任何消息
        return RenderedTokens(
            token_ids=token_ids,
            message_indices=indices,
            sampled_mask=[False] * len(token_ids),
            is_content=[idx >= 0 for idx in indices],
            message_roles=roles,
        )

    def render_ids(self, messages, tools=None, add_generation_prompt=False):
        return self.render(
            messages, tools=tools, add_generation_prompt=add_generation_prompt
        ).token_ids

    def get_stop_token_ids(self):
        return list(_STOP_TOKEN_IDS)

    def parse_response(self, token_ids, tools=None):
        # 内容对 completion token ids 可辨识：断言解析确实吃的是 token-out。
        return ParsedResponse(content="tok:" + ",".join(map(str, token_ids)))

    def bridge_to_next_turn(self, *args, **kwargs):
        return None


class FakeRendererTrainClient(TrainClient):
    """覆写私有钩子 `_renderer_pool`，把 renderer 换成 FakeRenderer（见模块 docstring）。"""

    def __init__(self, openai: AsyncOpenAI) -> None:
        super().__init__(openai)
        self.fake_renderer = FakeRenderer()

    def _renderer_pool(self, model, *, chat_template_kwargs=None):
        return self.fake_renderer


@dataclass
class RecordedRequest:
    path: str
    headers: dict = field(default_factory=dict)
    body: dict = field(default_factory=dict)


class FakeGenerateEngine:
    """记录请求的假 token-in/token-out 引擎（vLLM /inference/v1/generate 形状）。"""

    def __init__(self) -> None:
        self.requests: list[RecordedRequest] = []
        self.base_url: str | None = None
        self._runner: web.AppRunner | None = None

    async def _models(self, request: web.Request) -> web.Response:
        # renderers.client 会先 GET /v1/models 探测 max_model_len（预检 overlong）。
        return web.json_response(
            {
                "object": "list",
                "data": [
                    {"id": "fake-model", "object": "model", "max_model_len": 4096}
                ],
            }
        )

    async def _generate(self, request: web.Request) -> web.Response:
        self.requests.append(
            RecordedRequest(
                path=request.path,
                headers=dict(request.headers),
                body=await request.json(),
            )
        )
        return web.json_response(
            {
                "request_id": "req-contract-1",
                "choices": [
                    {
                        "index": 0,
                        "token_ids": list(_COMPLETION_IDS),
                        "logprobs": {
                            "content": [
                                {"logprob": lp} for lp in _COMPLETION_LOGPROBS
                            ]
                        },
                        "finish_reason": "stop",
                    }
                ],
            }
        )

    async def __aenter__(self) -> "FakeGenerateEngine":
        app = web.Application()
        app.router.add_get("/v1/models", self._models)
        # 注意挂载点：/inference/v1/generate 在服务根，不在 /v1 前缀下。
        app.router.add_post("/inference/v1/generate", self._generate)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        self.base_url = f"http://127.0.0.1:{port}/v1"
        return self

    async def __aexit__(self, *exc) -> None:
        if self._runner is not None:
            await self._runner.cleanup()


async def _one_turn(engine: FakeGenerateEngine) -> vf.Response:
    """对假引擎完成一次 get_response：单条 user 消息，session_id 固定。"""
    client = FakeRendererTrainClient(
        AsyncOpenAI(base_url=engine.base_url, api_key="test-key", max_retries=0)
    )
    try:
        return await client.get_response(
            ChatDialect(),
            {"messages": [{"role": "user", "content": "hello"}]},
            "fake-model",
            vf.SamplingConfig(temperature=0.5, max_tokens=16),
            session_id="trace-abc123",
        )
    finally:
        await client.close()


# ---------------------------------------------------------------------------
# 断言 1：请求体走 token-in
# ---------------------------------------------------------------------------


async def test_request_carries_token_ids_not_messages():
    async with FakeGenerateEngine() as engine:
        await _one_turn(engine)

    (req,) = engine.requests
    # 端点：/inference/v1/generate（服务根挂载）。
    assert req.path == "/inference/v1/generate"
    assert req.body["model"] == "fake-model"
    # token-in：请求体带 renderer 渲染出的 prompt token ids，不带文本 messages。
    assert req.body["token_ids"] == _EXPECTED_PROMPT_IDS
    assert "messages" not in req.body

    sp = req.body["sampling_params"]
    # 采样参数透传 + 两个强制字段：renderer 的 stop_token_ids、logprobs=1。
    assert sp["temperature"] == 0.5
    assert sp["max_tokens"] == 16
    assert sp["stop_token_ids"] == _STOP_TOKEN_IDS
    assert sp["logprobs"] == 1
    assert sp["skip_special_tokens"] is False
    # rollout 亲和路由头：同一 rollout 的多轮请求带同一 session id。
    assert req.headers.get(SESSION_ID_HEADER) == "trace-abc123"


# ---------------------------------------------------------------------------
# 断言 2：响应解析出 token_ids + 逐 token logprobs 且对齐
# ---------------------------------------------------------------------------


async def test_response_parses_token_ids_and_aligned_logprobs():
    async with FakeGenerateEngine() as engine:
        response = await _one_turn(engine)

    tokens = response.tokens
    assert tokens is not None
    assert tokens.prompt_ids == _EXPECTED_PROMPT_IDS
    assert tokens.completion_ids == _COMPLETION_IDS
    # 逐 token logprobs：长度与 completion_ids 一致、值一一对应。
    assert tokens.completion_logprobs == _COMPLETION_LOGPROBS
    assert len(tokens.completion_logprobs) == len(tokens.completion_ids)
    # message_spans：renderer 归因转成的每消息 token 区间（user 占 [0,2)；
    # generation prompt 是脚手架不归属消息）。
    assert tokens.message_spans == [(0, 2)]

    assert response.finish_reason == "stop"
    # 内容来自对 completion token ids 的解析（token-out 驱动，不是文本中继）。
    assert response.message.content == "tok:201,202,203"
    # usage 由 token ids 计数得出。
    assert response.usage is not None
    assert response.usage.prompt_tokens == len(_EXPECTED_PROMPT_IDS)
    assert response.usage.completion_tokens == len(_COMPLETION_IDS)
    # raw 回填 chat.completion 兼容响应（interception server 原样交给 harness 程序）。
    assert response.raw is not None
    assert response.raw["object"] == "chat.completion"
    assert response.raw["choices"][0]["message"]["content"] == "tok:201,202,203"


# ---------------------------------------------------------------------------
# 断言 3：TrainClient 的 Response 与 Trace 图闭环（token identity 成立）
# ---------------------------------------------------------------------------


async def test_response_commits_into_token_identical_branch():
    async with FakeGenerateEngine() as engine:
        response = await _one_turn(engine)

    trace = vf.Trace(task=vf.Task(idx=0, prompt="hello"))
    graph.prepare_turn(trace, [vf.UserMessage(content="hello")]).commit(response)

    assert trace.num_branches == 1
    branch = trace.branches[0]
    assert branch.token_ids == _EXPECTED_PROMPT_IDS + _COMPLETION_IDS
    assert branch.sampled_mask == [False] * 4 + [True] * 3
    assert branch.logprobs == [0.0] * 4 + _COMPLETION_LOGPROBS
