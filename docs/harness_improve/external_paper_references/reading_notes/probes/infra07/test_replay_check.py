"""离线合同、数学反例及 HTTP 协议测试；不导入或复现 SGLang/miles。"""
import copy
import io
import json
import math
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import platform
import sys
import tempfile
import threading
import unittest

import replay_check as rc

try:
    import torch
except ImportError:
    torch = None


def fixture():
    return {"schema": rc.SCHEMA, "contract": rc.contract("toy-fixed-weights", "toy-vocab-v1"),
            "execution": {"backend": "synthetic-fixture-not-model"},
            "records": [{"id": "turn-a", "input_ids": [1, 2, 3, 4], "positions": [1, 2, 3],
                         "mask": [1, 0, 1], "logprobs": [-1.0, None, -2.0],
                         "weight_labels": ["v1", "v1", "v1"]}]}


class ContractTests(unittest.TestCase):
    def test_equal_pair(self):
        self.assertEqual(rc.compare(fixture(), fixture(), atol=0)["status"], "PASS")

    def test_reordered_records_join_by_identity(self):
        a = fixture(); b = copy.deepcopy(a["records"][0]); b["id"] = "turn-b"
        a["records"].append(b); candidate = copy.deepcopy(a); candidate["records"].reverse()
        self.assertEqual(rc.compare(a, candidate, atol=0)["status"], "PASS")

    def test_duplicate_identity_rejected(self):
        a = fixture(); a["records"] *= 2
        self.assertEqual(rc.compare(a, fixture(), atol=0)["status"], "INCOMPARABLE")

    def test_missing_record_not_silently_dropped(self):
        a = fixture(); a["records"] = []
        self.assertEqual(rc.compare(a, fixture(), atol=0)["status"], "INCOMPARABLE")

    def test_same_length_different_tokens_rejected(self):
        a = fixture(); a["records"][0]["input_ids"][0] = 9
        self.assertEqual(rc.compare(fixture(), a, atol=1)["status"], "INCOMPARABLE")

    def test_same_text_hypothesis_does_not_override_token_ids(self):
        a = fixture(); a["records"][0]["input_ids"] = [8, 2, 3, 4]
        a["text"] = "same visible string"
        self.assertEqual(rc.compare(fixture(), a, atol=0)["status"], "INCOMPARABLE")

    def test_malformed_root_rejected(self):
        self.assertEqual(rc.compare([], fixture(), atol=0)["status"], "INCOMPARABLE")

    def test_masked_context_difference_rejected(self):
        a = fixture(); a["records"][0]["attention_mask"] = [1, 1, 0, 1]
        self.assertEqual(rc.compare(fixture(), a, atol=0)["status"], "INCOMPARABLE")

    def test_capture_rejects_unsupported_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.json"
            rc.write_json(path, {"cases": [{"id": "a", "input_ids": [1, 2], "position_ids": [0, 100]}]})
            with self.assertRaises(rc.ContractError):
                rc.cases_from(path)

    def test_position_zero_rejected(self):
        a = fixture(); a["records"][0]["positions"][0] = 0
        self.assertEqual(rc.compare(a, a, atol=0)["status"], "INCOMPARABLE")

    def test_probability_semantics_must_match(self):
        a = fixture(); a["contract"]["probability"]["temperature"] = .7
        self.assertEqual(rc.compare(fixture(), a, atol=0)["status"], "INCOMPARABLE")

    def test_versions_checked_per_scored_position(self):
        a = fixture(); a["records"][0]["weight_labels"][-1] = "v2"
        self.assertEqual(rc.compare(fixture(), a, atol=0)["status"], "INCOMPARABLE")

    def test_all_masked_is_insufficient(self):
        a = fixture(); a["records"][0]["mask"] = [0, 0, 0]
        self.assertEqual(rc.compare(a, a, atol=0)["status"], "INSUFFICIENT")

    def test_nan_is_not_replaced_by_zero(self):
        a = fixture(); a["records"][0]["logprobs"][0] = float("nan")
        self.assertEqual(rc.compare(a, a, atol=0)["status"], "INCOMPARABLE")

    def test_observation_placeholder_not_in_statistics(self):
        a = fixture(); a["records"][0]["logprobs"][1] = -100
        result = rc.compare(fixture(), a, atol=0)
        self.assertEqual(result["status"], "PASS"); self.assertEqual(result["active_tokens"], 2)

    def test_signed_cancellation_not_false_pass(self):
        a = fixture(); a["records"][0]["logprobs"] = [-.9, None, -2.1]
        result = rc.compare(fixture(), a, atol=.01)
        self.assertAlmostEqual(result["mean_signed"], 0)
        self.assertEqual(result["status"], "FAIL")

    def test_ess_one_does_not_imply_ratio_one(self):
        a = fixture(); a["records"][0]["logprobs"] = [-2.0, None, -3.0]
        result = rc.compare(fixture(), a, atol=.01)
        self.assertAlmostEqual(result["normalized_ratio_ess"], 1)
        self.assertEqual(result["ratio_outside_fraction"], 1)
        self.assertEqual(result["status"], "FAIL")

    def test_support_membership_required(self):
        a = fixture(); a["contract"]["probability"]["kind"] = "fixed_retained_support"
        a["records"][0]["support_ids"] = [[2], [3], [1, 2]]
        self.assertEqual(rc.compare(a, a, atol=0)["status"], "INCOMPARABLE")

    def test_support_changes_not_numerical_difference(self):
        a = fixture(); a["contract"]["probability"]["kind"] = "fixed_retained_support"
        a["records"][0]["support_ids"] = [[2, 5], [3], [4, 5]]
        b = copy.deepcopy(a); b["records"][0]["support_ids"][0] = [2, 6]
        self.assertEqual(rc.compare(a, b, atol=0)["status"], "INCOMPARABLE")

    def test_declared_routing_mismatch_rejected(self):
        a = fixture(); a["records"][0]["routing_ids"] = [[0, 2], [1, 3], [2, 3]]
        self.assertEqual(rc.compare(fixture(), a, atol=0)["status"], "INCOMPARABLE")

    def test_large_log_ratio_does_not_overflow(self):
        a = fixture(); b = fixture()
        a["records"][0]["logprobs"] = [-2000, None, -1000]
        b["records"][0]["logprobs"] = [-1, None, -1]
        result = rc.compare(a, b, atol=.001)
        self.assertEqual(result["status"], "FAIL")
        json.dumps(result, allow_nan=False)


class MathTests(unittest.TestCase):
    def test_actual_retained_mass_not_top_p_parameter(self):
        # 保留两项的真实质量是0.9，不是传入阈值0.8。
        p = [.6, .3, .1]; mass = sum(p[:2]); q = p[0] / mass
        self.assertAlmostEqual(math.log(p[0]) - math.log(q), math.log(.9))
        self.assertNotAlmostEqual(mass, .8)
        self.assertAlmostEqual(math.exp(16 * math.log(mass)), .9 ** 16)

    def test_target_outside_behavior_support_not_recovered(self):
        # 重要性重加权在保留集内能恢复p的贡献，却无法观察集合外的0.1。
        p = [.6, .3, .1]; q = [2/3, 1/3]
        recovered_total = sum(q[i] * p[i] / q[i] for i in range(2))
        self.assertAlmostEqual(recovered_total, .9)
        self.assertNotAlmostEqual(recovered_total, 1)

    def test_three_probabilities_factorization(self):
        behavior, old_actor, current = .2, .3, .4
        self.assertAlmostEqual((current / old_actor) * (old_actor / behavior), current / behavior)

    def test_greedy_returned_model_logprob_not_behavior_delta(self):
        self.assertNotEqual(math.log(.6), 0)
        self.assertEqual(math.log(1.0), 0)

    @unittest.skipIf(torch is None, "未安装 torch：不声称检查 autograd")
    def test_same_forward_different_gradient(self):
        x = torch.tensor(-1., dtype=torch.float64, requires_grad=True)
        ratio = (x + 1).exp()
        a = -ratio.detach() * x; b = -ratio * x
        self.assertEqual(a.item(), b.item())
        ga = torch.autograd.grad(a, x, retain_graph=True)[0].item()
        gb = torch.autograd.grad(b, x)[0].item()
        self.assertEqual(ga, -1.); self.assertEqual(gb, 0.)

    @unittest.skipIf(torch is None, "未安装 torch")
    def test_zero_times_nan_is_not_safe_mask(self):
        x = torch.tensor([float("nan"), -1.])
        mask = torch.tensor([False, True])
        self.assertTrue(torch.isnan((x * mask).sum()).item())
        self.assertEqual(torch.where(mask, x, torch.zeros_like(x)).sum().item(), -1.)

    @unittest.skipIf(torch is None, "未安装 torch")
    def test_log_softmax_and_log_of_softmax_underflow(self):
        x = torch.tensor([0., -1000.], dtype=torch.float32)
        self.assertTrue(torch.isfinite(x.log_softmax(0)[1]).item())
        self.assertTrue(torch.isneginf(x.softmax(0).log()[1]).item())

    @unittest.skipIf(torch is None, "未安装 torch")
    def test_shift_invariant_log_normalizer(self):
        x = torch.tensor([[1e8, 1e8]], dtype=torch.float32)
        naive = x - torch.logsumexp(x, -1, keepdim=True)
        shifted = (x - x.max(-1, keepdim=True).values).log_softmax(-1)
        self.assertFalse(torch.allclose(naive, shifted))
        self.assertAlmostEqual(shifted[0, 0].item(), -math.log(2), places=6)

    @unittest.skipIf(torch is None, "未安装 torch")
    def test_selected_logprob_requires_previous_logits_row(self):
        logits = torch.tensor([[5., 0., 0.], [0., 5., 0.], [0., 0., 5.]], dtype=torch.float64)
        ids = torch.tensor([2, 0, 1])
        correct = logits[:2].log_softmax(-1).gather(1, ids[1:, None]).squeeze(-1)
        wrong = logits[1:].log_softmax(-1).gather(1, ids[1:, None]).squeeze(-1)
        self.assertTrue(torch.all(correct > wrong).item())


class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.received = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                cls.received.append(data)
                pairs = [[None if i == 0 else -float(i), token, None] for i, token in enumerate(data["input_ids"])]
                if self.path.startswith("/wrong"):
                    pairs[-1][1] += 1
                body = json.dumps({"meta_info": {"input_token_logprobs": pairs, "weight_version": "mock-v1"}}).encode()
                self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True); cls.thread.start()
        cls.endpoint = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()

    def test_http_payload_and_shift_are_explicit(self):
        row = rc.score_sglang_case(self.endpoint, fixture()["records"][0], weights="fixed", timeout=5)
        self.assertEqual(row["logprobs"], [-1., -2., -3.])
        self.assertEqual(self.received[-1]["sampling_params"]["max_new_tokens"], 0)
        self.assertEqual(self.received[-1]["input_ids"], [1, 2, 3, 4])
        self.assertEqual(self.received[-1]["logprob_start_len"], 0)

    def test_http_wrong_token_id_rejected(self):
        with self.assertRaises(rc.ContractError):
            rc.score_sglang_case(self.endpoint + "/wrong", fixture()["records"][0], weights="fixed", timeout=5)

    def test_capture_concurrency_preserves_record_identity(self):
        import argparse
        with tempfile.TemporaryDirectory() as tmp:
            cases = Path(tmp) / "cases.json"; output = Path(tmp) / "out.json"
            rc.write_json(cases, {"cases": [{"id": "a", "input_ids": [1, 2, 3]}, {"id": "b", "input_ids": [4, 5]}]})
            args = argparse.Namespace(endpoint=self.endpoint, allow_remote=False, repeats=2, concurrency=4, timeout=5,
                                      cases=str(cases), output=str(output), weights="fixed", tokenizer="toy")
            rc.capture(args)
            doc = rc.read_json(output)
            self.assertEqual(len(rc.validate(doc)), 4)
            self.assertEqual([r["id"] for r in doc["records"]], ["a::r0", "b::r0", "a::r1", "b::r1"])


def run():
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    names = [case.id() for group in suite for case in group]
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    print(stream.getvalue())
    numbers = {"retained_mass": .9, "logprob_offset": math.log(.9), "16_token_ratio": .9 ** 16,
               "wrong_assumption_top_p_power": .8 ** 16}
    evidence = {"date": "2026-09-08", "tests_run": result.testsRun, "failures": len(result.failures),
                "errors": len(result.errors), "skipped": len(result.skipped), "test_ids": names,
                "environment": {"python": sys.version, "platform": platform.platform(), "torch": torch.__version__ if torch else None,
                                "cuda_available": torch.cuda.is_available() if torch else False},
                "numbers": numbers, "log": stream.getvalue(),
                "scope": "独立 CPU 数学/合同/本地 mock HTTP 检查；没有运行真实 SGLang、vLLM、miles、HF 模型或 GPU"}
    if "--output" in sys.argv:
        rc.write_json(sys.argv[sys.argv.index("--output") + 1], evidence)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(run())
