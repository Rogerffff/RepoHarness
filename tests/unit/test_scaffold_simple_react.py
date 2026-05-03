from repo_harness.scaffolds import build_scaffold


def test_simple_react_prompt_guides_durable_repository_patch():
    scaffold = build_scaffold("simple_react")

    assert scaffold.scaffold_version == "repo_harness_simple_react_v1"
    assert "durable repository change" in scaffold.prompt_fragment
    assert "temporary diagnostic scripts" in scaffold.prompt_fragment
    assert "removed before the final diff" in scaffold.prompt_fragment
    assert "when available in allowed_tools" in scaffold.prompt_fragment
    assert "git_diff" in scaffold.prompt_fragment
    assert "run_tests" in scaffold.prompt_fragment


def test_simple_react_prompt_does_not_expose_hidden_evaluator_terms():
    scaffold = build_scaffold("simple_react")
    lowered = scaffold.prompt_fragment.lower()

    forbidden_terms = [
        "hidden selector",
        "fail_to_pass",
        "pass_to_pass",
        "test_patch",
        "gold patch",
        "gold_patch",
        "hidden verifier",
        "hidden result",
        "final verifier hidden result",
        "run outcome",
        "reward/run outcome",
    ]
    assert not any(term in lowered for term in forbidden_terms)
