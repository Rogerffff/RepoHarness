# 公开开发检查（来源：batch02 public_read.md 的 C1–C5；只含公开内容；dummy 凭据、本地 mock，不访问 AWS）。
step() { echo "=== STEP $1"; shift; "$@"; echo "=== RC $?"; }
export TEST_SERVER_MODE=false AWS_DEFAULT_REGION=eu-west-1 AWS_ACCESS_KEY_ID=testing AWS_SECRET_ACCESS_KEY=testing AWS_SESSION_TOKEN=testing
step c1_import python - <<'PY'
import sys
import boto3, botocore, moto, pytest, sure
import moto.events.models as events_models
import moto.logs.models as logs_models
print(sys.executable, sys.version)
print(moto.__file__, events_models.__file__, logs_models.__file__)
print(boto3.__version__, botocore.__version__, moto.__version__)
PY
step c2_exists_matrix python - <<'PY'
import json
from moto.events.models import EventPattern
cases = [{"detail": {"foo": None}}, {"detail": {}}, {"detail": {"foo": "123"}}, {"detail": {"foo": {"bar": "baz"}}}]
for exists, expected in [(True, [True, False, True, False]), (False, [False, True, False, True])]:
    pattern = EventPattern.load(json.dumps({"detail": {"foo": [{"exists": exists}]}}))
    actual = [pattern.matches_event(event) for event in cases]
    print(exists, actual)
    assert actual == expected, (exists, actual, expected)
PY
step c3_pattern_tests python -m pytest -q tests/test_events/test_event_pattern.py
step c3_logs_test python -m pytest -q tests/test_events/test_events_integration.py::test_send_to_cw_log_group
step c4_logs_delivery python - <<'PY'
import json
import boto3
from moto import mock_events, mock_logs
from moto.core import ACCOUNT_ID
expected = [{"foo": "123", "bar": "123"}, {"foo": None, "bar": "123"}]
pattern = {"source": ["test-source"], "detail-type": ["test-detail-type"],
           "detail": {"foo": [{"exists": True}], "bar": [{"exists": True}]}}
with mock_events(), mock_logs():
    events = boto3.client("events", region_name="eu-west-1")
    logs = boto3.client("logs", region_name="eu-west-1")
    logs.create_log_group(logGroupName="test-log-group")
    events.create_event_bus(Name="test-event-bus")
    events.put_rule(Name="test-event-rule", State="ENABLED", EventBusName="test-event-bus", EventPattern=json.dumps(pattern))
    events.put_targets(Rule="test-event-rule", EventBusName="test-event-bus",
                       Targets=[{"Id": "123", "Arn": f"arn:aws:logs:eu-west-1:{ACCOUNT_ID}:log-group:test-log-group"}])
    events.put_events(Entries=[{"EventBusName": "test-event-bus", "Source": "test-source",
                                "DetailType": "test-detail-type", "Detail": json.dumps(detail)} for detail in expected])
    received = logs.filter_log_events(logGroupName="test-log-group")["events"]
    details = [json.loads(event["message"])["detail"] for event in received]
    print(details)
    assert len(details) == 2 and all(detail in details for detail in expected), details
PY
step c5_compile python -m py_compile moto/events/models.py
step git_status git status --porcelain
