"""R1 主审补证：直接构造真实 BringupService，检查已登记路由是否接到新 wrapper。

复用现有离线 tokenizer / 本机 HTTP 线程夹具；不调用 async_start、Docker、CC 或推理 API。
fa_audit_only 与 fa_formal 共用的路由安装段位于任务面分流之前；此处使用冻结本地任务文件。
"""
import asyncio
import json
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import cap_body_race_probe as old

sys.path.insert(0, str(old.ROOT / "rh2/tests/adapters"))
from test_w3b_bringup_sandbox_runtime import _service


async def main():
    with tempfile.TemporaryDirectory(prefix="bringup-route-", dir=HERE) as temp, pytest.MonkeyPatch.context() as mp:
        _, service = _service(mp, Path(temp), mode="fa_audit_only", docker=None)
        try:
            route = next(r for r in service.adapter.app.router.routes()
                         if r.method == "POST" and r.resource.canonical == "/v1/messages")
            facts = {"entry": "BringupService.__init__", "route_handler": route.handler.__func__.__name__,
                     "current_method": service.adapter._run_turn.__func__.__name__,
                     "route_uses_current_method": route.handler.__func__ is service.adapter._run_turn.__func__,
                     "real_http_thread_constructed": service.app_handle.port > 0,
                     "cap": service.adapter.max_turns_per_sid}
            assert facts["route_handler"] == "_run_turn" and facts["current_method"] == "rh2_run_turn"
            assert not facts["route_uses_current_method"]  # 确认当前缺陷；修后应改为接到 wrapper。
        finally:
            service.app_handle.stop()
        facts["http_handle_stopped"] = True
        print(json.dumps(facts, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
