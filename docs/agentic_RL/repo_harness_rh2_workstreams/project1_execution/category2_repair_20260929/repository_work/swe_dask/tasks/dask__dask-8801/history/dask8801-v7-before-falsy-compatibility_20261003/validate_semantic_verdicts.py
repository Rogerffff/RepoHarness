"""宿主核裁决完整性与引用原文；不按关键词重新替模型裁定自然语言。"""
import json


def visible_texts(value):
    texts = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ("message", "displayed_type") and isinstance(item, str):
                texts.append(item)
            elif key in ("visible_notes", "notes") and isinstance(item, list):
                texts.extend(n for n in item if isinstance(n, str))
            elif isinstance(item, (dict, list)):
                texts.extend(visible_texts(item))
    elif isinstance(value, list):
        for item in value:
            texts.extend(visible_texts(item))
    return texts


def validate(inputs, output):
    issues, results = [], {}
    by_id = {}
    if not isinstance(inputs, list) or not inputs:
        return {"state": "needs_evidence", "issues": ["input_collection_missing_or_invalid"], "results": {}}
    for item in inputs:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or item["id"] in by_id:
            return {"state": "needs_evidence", "issues": ["input_id_invalid_or_duplicate"], "results": {}}
        if not isinstance(item.get("semantic_judge_input"), dict):
            return {"state": "needs_evidence", "issues": ["semantic_judge_input_missing_or_invalid"], "results": {}}
        by_id[item["id"]] = item["semantic_judge_input"]
    if not isinstance(output, dict) or output.get("schema") != "dask8801_semantic_verdicts.v1" or not isinstance(output.get("results"), list):
        return {"state": "needs_review", "issues": ["judge_output_schema_invalid"], "results": {}}
    for item in output["results"]:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or item["id"] not in by_id:
            issues.append("unknown_or_invalid_output_id")
            continue
        identifier = item["id"]
        if identifier in results:
            issues.append("duplicate_output_id:" + identifier)
            continue
        results[identifier] = item
        verdict = item.get("verdict")
        if not isinstance(verdict, str) or verdict not in {"pass", "fail", "uncertain"}:
            issues.append("invalid_verdict:" + identifier)
        if not isinstance(item.get("explanation"), str) or not item["explanation"].strip():
            issues.append("missing_explanation:" + identifier)
        payload = by_id[identifier]
        diagnostic = {k: v for k, v in payload.items() if k != "trusted_facts"}
        texts = visible_texts(diagnostic)
        for field in ("file_evidence", "reason_evidence", "contradiction_evidence"):
            evidence = item.get(field)
            if not isinstance(evidence, list) or not all(isinstance(e, str) and bool(e) for e in evidence):
                issues.append("invalid_evidence_list:" + identifier + ":" + field)
                continue
            if verdict == "pass" and field != "contradiction_evidence" and not evidence:
                issues.append("pass_evidence_missing:" + identifier + ":" + field)
            if verdict == "pass" and field == "contradiction_evidence" and evidence:
                issues.append("pass_with_contradiction_evidence:" + identifier)
            if any(not any(e in text for text in texts) for e in evidence):
                issues.append("citation_not_in_visible_diagnostic:" + identifier + ":" + field)
    issues.extend("missing_output_id:" + identifier for identifier in sorted(set(by_id) - set(results)))
    return {"state": "needs_review" if issues else "complete", "issues": issues, "results": results}


def read(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError, RecursionError) as exc:
        return {"judge_service_error": type(exc).__name__}
