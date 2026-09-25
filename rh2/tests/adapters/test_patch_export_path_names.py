"""Codex review_next_slices §6（E2/E4 调查发现）：候选在 /testbed 建含控制字符（如 0x01）的文件名 → 运行后 census 解析抛
pydantic ValidationError，旧 exporter 不捕获，编排按 `rh2_contract_validation_failed` 升 run-fatal——模型能让整场训练停下。

处置（既有不支持候选工件的补漏，不是新政策）：在候选路径的解析边界给 typed 不支持原因，复用既有 unsafe 通道（present + 永久
拒绝、不评分），证据里的路径把控制字符写成 `\\xNN`。**只有**用契约自己的路径规则复查到候选条目路径违规才改判；没有候选
路径违规的 ValidationError（我方身份 / 摘要 / 契约矛盾）照旧上抛、保持 run-fatal。

三个对照（Codex 要求）：正常文件、控制字符路径、我方契约矛盾；另走一次真实编排确认不再 run-fatal、拒绝证据进 receipt。
"""

from __future__ import annotations

import base64
import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_f2_2_capability import _stamp_fa_identity  # noqa: E402
from test_slime_generate import SAMPLING_PARAMS, _Args, _formal_config, build_dense_chain, dense_turns  # noqa: E402

from repoharness2.adapters.slime.generate import QuiescenceConfirmed  # noqa: E402
from repoharness2.adapters.slime.patch_exporter import (  # noqa: E402
    UNSUPPORTED_PATH_NAME,
    PatchExportError,
    export_frozen_patch,
)
from repoharness2.contracts.baseline_manifest import (  # noqa: E402
    BASELINE_MANIFEST_POLICY_V1,
    BaselineWorkspaceManifestV1,
    compute_policy_digest,
)

BASE = "a" * 40


def _baseline() -> BaselineWorkspaceManifestV1:
    return BaselineWorkspaceManifestV1(
        task_id="t", workdir="/testbed", public_bundle_digest="sha256:" + "e" * 64,
        runtime_image_digest="sha256:" + "1" * 64, materialized_head=BASE, task_base_commit=BASE,
        policy=BASELINE_MANIFEST_POLICY_V1, policy_digest=compute_policy_digest(BASELINE_MANIFEST_POLICY_V1),
        entries=(),
    )


class _Ws:
    def __init__(self, census: str, contents: str = "") -> None:
        self.census, self.contents = census, contents

    async def run_bash(self, script):
        if "find ." in script:
            return SimpleNamespace(exit_code=0, stdout=self.census, stderr="")
        return SimpleNamespace(exit_code=0, stdout=self.contents, stderr="")


def _regular(path: str, content: bytes = b"x\n") -> tuple[str, str]:
    sha = hashlib.sha256(content).hexdigest()
    return f"regular\t100644\t{sha}\t{path}\n", f"{path}\t{base64.b64encode(content).decode()}\n"


async def test_normal_new_file_still_exports():
    census, contents = _regular("src/a.py")
    art = await export_frozen_patch(_Ws(census, contents), _baseline(), rollout_execution_id="e", physical_attempt_id="e#p1-aaaa")
    assert [e.path for e in art.entries] == ["src/a.py"]


@pytest.mark.parametrize(("raw", "shown"), [
    ("src/a\x01b.py", "src/a\\x01b.py"),
    ("src/\x1fname.py", "src/\\x1fname.py"),
    ("src/del\x7f.py", "src/del\\x7f.py"),
    ("src/esc\x1b[31m.py", "src/esc\\x1b[31m.py"),
])
async def test_candidate_path_with_control_characters_becomes_a_typed_unsupported_object(raw, shown):
    ok_line, _ = _regular("src/ok.py")
    bad_line, _ = _regular(raw)
    sink: dict[str, float] = {}
    with pytest.raises(PatchExportError) as err:
        await export_frozen_patch(_Ws(ok_line + bad_line), _baseline(), rollout_execution_id="e",
                                  physical_attempt_id="e#p1-aaaa", segment_sink=sink)
    assert err.value.reason_code == "unsupported_object_in_patch"  # 既有 unsafe 通道的 reason code
    assert err.value.object_type == UNSUPPORTED_PATH_NAME == "unsupported_path_name"
    assert err.value.object_path == shown and all(ch >= "\x20" and ch != "\x7f" for ch in err.value.object_path)
    assert isinstance(err.value.__cause__, ValidationError)  # 原始契约拒绝留在异常链里
    assert set(sink) == {"post_census"}


@pytest.mark.parametrize("census", [
    # 条目落在排除 namespace：census 本应把它排除，出现在条目里是我方矛盾（manifest 级校验）
    _regular(".harness/leak.py")[0],
    # 同一路径两条：find 不会产出，出现即我方矛盾
    _regular("src/a.py")[0] + _regular("src/a.py", b"y\n")[0],
])
async def test_our_own_contract_contradictions_still_raise_the_validation_error(census):
    with pytest.raises(ValidationError):
        await export_frozen_patch(_Ws(census), _baseline(), rollout_execution_id="e", physical_attempt_id="e#p1-aaaa")


async def test_formal_chain_routes_the_control_character_path_to_the_unsafe_channel_not_run_fatal():
    """真实编排（fa_formal）：post-run census 出现候选的控制字符路径 → present + 永久拒绝（交付、不评分），receipt 是
    delivery_prepared、拒绝证据内嵌；不再是 fatal_run_halt。"""

    _line, _ = _regular("src/evil\x01name.py")

    class _BadNameWs:
        def __init__(self, underlying) -> None:
            self._u = underlying

        async def run_bash(self, script):
            if "find ." in script:
                return SimpleNamespace(exit_code=0, stdout=_line, stderr="")
            return await self._u.run_bash(script)

    class _Barrier:
        async def establish(self, *, workspace, audit):
            return QuiescenceConfirmed(frozen_grading_workspace=_BadNameWs(workspace), snapshot_ref="sha256:abc",
                                       evidence_refs=("s",))

    turns = dense_turns()
    for turn in turns:
        turn.response["meta_info"]["weight_version"] = "5"
    chain = build_dense_chain(config=_formal_config(policy_version="5", execution_mode="fa_formal"),
                              runtime_quiescence_barrier=_Barrier(), turns=turns)
    _stamp_fa_identity(chain.base_sample)
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    assert all(getattr(x, "remove_sample", True) is False for x in delivered)
    receipt = chain.finalization.receipts[0]
    assert receipt.attempt_disposition == "delivery_prepared"
    evidence = receipt.rejection_evidence
    assert evidence is not None and evidence.reason_code == "unsupported_object_in_patch"
    assert evidence.object_type == "unsupported_path_name" and evidence.object_path == "src/evil\\x01name.py"
    assert receipt.frozen_patch_digest is None
    audit = chain.orchestrator.audits[-1]
    assert audit.unsafe_artifact_reasons == ["unsupported_object_in_patch:src/evil\\x01name.py:unsupported_path_name"]
    assert not chain.grading.calls  # 不评分
