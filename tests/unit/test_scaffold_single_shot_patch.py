import json

import pytest

from repo_harness.config import RunConfig
from repo_harness.errors import ConfigError
from repo_harness.run_metadata.tool_snapshot import build_tool_schema_snapshot
from repo_harness.scaffolds import build_scaffold, resolve_allowed_tools, resolve_feedback_policy
from repo_harness.scaffolds.patch_action import parse_patch_action
from repo_harness.tools import ToolRegistry


def test_single_shot_patch_scaffold_resolves_disabled_feedback_policy():
    scaffold = build_scaffold("single_shot_patch")
    policy = resolve_feedback_policy(
        run_config=RunConfig.model_validate({"runtime": {"scaffold_id": "single_shot_patch"}}),
        scaffold=scaffold,
    )

    assert scaffold.scaffold_id == "single_shot_patch"
    assert policy.resolved_test_feedback_policy == "disabled"
    assert policy.resolved_feedback_tests_passed_policy == "not_applicable"
    assert resolve_allowed_tools(scaffold=scaffold, feedback_policy=policy) == []


def test_single_shot_patch_rejects_runtime_test_feedback_override():
    scaffold = build_scaffold("single_shot_patch")
    config = RunConfig.model_validate(
        {
            "runtime": {
                "scaffold_id": "single_shot_patch",
                "test_feedback_policy": "oracle_hidden_feedback",
            }
        }
    )

    with pytest.raises(ConfigError, match="requires test_feedback_policy=disabled"):
        resolve_feedback_policy(run_config=config, scaffold=scaffold)


def test_empty_tool_schema_snapshot_is_valid_for_single_shot_patch():
    snapshot = build_tool_schema_snapshot(ToolRegistry([]))

    assert snapshot.tool_order == []
    assert snapshot.tools == []


def test_patch_action_parser_accepts_fenced_diff():
    result = parse_patch_action(
        """
Here is the patch:

```diff
diff --git a/calculator.py b/calculator.py
--- a/calculator.py
+++ b/calculator.py
@@ -1 +1 @@
-old
+new
```
""".strip()
    )

    assert result.success is True
    assert result.changed_paths == ["calculator.py"]
    assert result.patch_text.startswith("diff --git")


def test_patch_action_parser_rejects_missing_diff():
    result = parse_patch_action("I fixed it.")

    assert result.success is False
    assert result.error_type == "missing_unified_diff"


def test_patch_action_replay_step_hides_expected_outcome_comment():
    from repo_harness.model_client.schemas import ReplayScript

    script = ReplayScript.model_validate(
        {
            "script_id": "patch",
            "task_id": "task",
            "steps": [
                {
                    "step_id": "patch",
                    "action": "patch_action",
                    "patch_text": "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-a\n+b\n",
                    "expected_outcome": {"accepted": True},
                    "comment": "test-only note",
                }
            ],
        }
    )

    visible = json.dumps(script.model_visible_steps(), ensure_ascii=False)
    assert "expected_outcome" not in visible
    assert "test-only note" not in visible
    assert "patch_text" in visible
