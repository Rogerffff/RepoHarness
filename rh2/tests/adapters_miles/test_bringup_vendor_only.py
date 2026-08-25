"""B8 回归：无 reference/slime、只有 vendor（rh2/src/slime）时构造真实
BringupService——证明闭包补齐 processing_utils 后真实启动路径 import 全通。

背景（blockers §8）：bringup.py:574 在 `BringupService.__init__` 里函数内
`from slime.utils.processing_utils import load_tokenizer`；此前 18 文件闭包
缺该文件，而既有 314 个测试没有真实构造 BringupService，路径被掩盖。

范围界定：本测试只到 __init__ 完成（tokenizer/renderer/adapter 线程/
capture wire/冻结 8 题/评分队列全部就位）；`async_start` 的 startup_checks
需要真实 SGLang router，归硬件段。

tokenizer 事实记录：用本机 HF 缓存里的 Qwen/Qwen3-8B tokenizer（离线，
HF_HUB_OFFLINE=1；比任务书建议的 Qwen3-0.6B 更稳——0.6B 不在缓存而 8B 在，
tokenizer 文件与模型体积无关）。缓存/网络都不可用时 skip 并说明。
"""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

import pytest


def _strip_reference_slime_paths():
    """把 reference/slime 从 sys.path 摘掉（返回被摘条目，供恢复）。

    单独跑本目录时本来就没有；整仓混跑时其他目录插过，为满足"reference/slime
    不在 path"的验收条件在本测试内临时摘除。"""

    removed = [p for p in sys.path if "reference/slime" in p]
    for p in removed:
        sys.path.remove(p)
    return removed


def test_bringup_service_constructs_with_vendor_only(world, monkeypatch, tmp_path):
    removed = _strip_reference_slime_paths()
    try:
        # vendor-only 前置自证：path 无 reference/slime，slime 解析到 vendor
        assert not any("reference/slime" in p for p in sys.path)
        import slime

        assert Path(slime.__file__).resolve().is_relative_to(world.rh2_src)

        # B8 修复的直接证据：vendor 闭包里 processing_utils 可 import 且
        # 正是 bringup 函数内 import 的那条链
        import slime.utils.processing_utils as pu

        assert Path(pu.__file__).resolve().is_relative_to(world.rh2_src)
        assert callable(pu.load_tokenizer)

        import repoharness2.adapters.slime.bringup as bringup

        # 环境收口：artifact 目录进 tmp；adapter 用回环地址 + 随机端口
        #（bringup 模块级读环境变量，这里 patch 模块属性而不是环境）
        monkeypatch.setattr(bringup, "ARTIFACT_DIR", tmp_path / "artifacts")
        monkeypatch.setattr(bringup, "ADAPTER_BIND_HOST", "127.0.0.1")
        monkeypatch.setattr(bringup, "ADAPTER_PORT", 0)
        monkeypatch.setenv("HF_HUB_OFFLINE", "1")

        args = Namespace(
            hf_checkpoint="Qwen/Qwen3-8B",
            sglang_router_ip="127.0.0.1",
            sglang_router_port=59999,  # __init__ 只拼 URL，不发请求
            rollout_max_context_len=0,
            sglang_tool_call_parser=None,
            sglang_reasoning_parser=None,
        )

        try:
            service = bringup.BringupService(args)
        except OSError as exc:  # tokenizer 缓存缺失且离线——环境问题，不是闭包问题
            pytest.skip(f"本机无 Qwen3-8B tokenizer 缓存且离线，跳过：{exc}")

        try:
            # 真实启动面就位的证据
            assert service.tokenizer.encode("hello world")
            assert service.adapter_url.startswith("http://")
            assert len(service.task_specs) == 8  # 冻结 8 题
            assert service.renderer is not None

            # 全过程只加载 vendor slime 模块（零 reference 泄漏）
            loaded = {
                name: mod.__file__
                for name, mod in sys.modules.items()
                if name.split(".")[0] == "slime" and getattr(mod, "__file__", None)
            }
            assert loaded, "没有任何 slime 模块被加载？"
            for name, file in loaded.items():
                assert Path(file).resolve().is_relative_to(world.rh2_src), (name, file)
            # bringup 用到的三层关键模块确在其中
            assert "slime.utils.processing_utils" in loaded
            assert "slime.agent.adapters.anthropic" in loaded
            assert "slime.agent.aiohttp_threaded" in loaded
        finally:
            service.app_handle.stop()
    finally:
        for p in removed:
            sys.path.append(p)  # 恢复（顺序对后续目录无关紧要：它们自己 insert(0)）
