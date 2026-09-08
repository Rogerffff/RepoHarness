#!/usr/bin/env python3
"""Narrow CPU probes for Dressage@3e3142f; not a GPU/serving reproduction.

Run in a clean Python process (Python >=3.10, numpy installed):
  python dressage_cpu_probes_20260908.py --source-root /path/to/Dressage \
      --output dressage_cpu_results_20260908.json

Only three reviewed source modules are executed, after Git blob verification.
Heavy package initializers are not executed. The transport import is replaced
by its documented metadata-key constant; no TransferQueue backend is mocked as
working. Sample objects are explicit lightweight test doubles. These probes
must not be confused with the complete upstream test suite.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
import platform
from pathlib import Path
import sys
import types
import unittest

PIN = "3e3142fe8ea07e4504c3b20a936a4c201a3de44c"
SOURCES = {
    "dressage.proxy.rebalancing.greedy": ("dressage/proxy/rebalancing/greedy.py", "8d1bfe709461e29ee556873b6ceb29ba2edb2b21"),
    "dressage.training.reward_post_process": ("dressage/training/reward_post_process.py", "4b47ae8a944af45354cf993d4170f79d8f098941"),
    "dressage.rollout.convert_samples": ("dressage/rollout/convert_samples.py", "646dee74c2b0c410f7cca1b41f57cba60ef48253"),
}
G = R = C = None
NS = types.SimpleNamespace
OBS = {}


def load_sources(root: Path):
    # Verify every file before executing any upstream module.
    verified = {}
    for name, (relative, expected) in SOURCES.items():
        data = (root / relative).read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if actual != expected:
            raise RuntimeError(f"Unexpected source revision: {relative}: {actual} != {expected}")
        verified[relative] = actual
    for name in ("dressage", "dressage.proxy", "dressage.proxy.rebalancing", "dressage.training", "dressage.rollout"):
        module = types.ModuleType(name)
        module.__path__ = []
        sys.modules[name] = module
    transport = types.ModuleType("dressage.transport")
    transport.TQ_SAMPLE_REF_METADATA_KEY = "dressage_tq_sample_ref"
    sys.modules[transport.__name__] = transport
    modules = []
    for name, (relative, _) in SOURCES.items():
        spec = importlib.util.spec_from_file_location(name, root / relative)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot load {relative}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        modules.append(module)
    return modules, verified


def args(**overrides):
    values = dict(advantage_estimator="grpo", rewards_normalization=True,
                  grpo_std_normalization=False, reward_key=None, global_batch_size=4,
                  use_rollout_routing_replay=False, mopd_teacher_config=None)
    values.update(overrides)
    return NS(**values)


def sample(parent, prompt="p", group=0, segment=0, reward=0.0,
           mask=(1, 1), dead=False, logs=True):
    return NS(metadata=dict(parent_traj_id=parent, instance_id=prompt, segment_index=segment),
              group_index=group, index=segment, rollout_id=parent, reward=reward,
              remove_sample=dead, tokens=[0] + [1]*len(mask), response_length=len(mask),
              loss_mask=list(mask), status="completed", Status=NS(TRUNCATED="truncated"),
              rollout_log_probs=[-0.5]*len(mask) if logs else None,
              rollout_routed_experts=None, train_metadata=None,
              multimodal_train_inputs=None, teacher_log_probs=None)


def engine(url, tokens=0, requests=0, queue=0, usage=0):
    return G.EngineBaseline(url, requests, tokens, queue, 100, 1000, usage)


def edge(url, tokens=100):
    return G.FeasibleEdge("s", url, 1, tokens)


def decision(kind, owner, engines, edges, threshold=0.1):
    return G.choose_greedy_step(session_id="s", kind=kind, owner_engine_url=owner,
                               engines=engines, edges=edges,
                               min_load_improvement_ratio=threshold)


class RoutingProbes(unittest.TestCase):
    def test_01_additive_pressure(self):
        p = G.projected_pressure(engine("a", 300, 20, 10), queue_increment=2, token_increment=100)
        self.assertAlmostEqual(p.total, 0.72)

    def test_02_token_usage_floor(self):
        p = G.projected_pressure(engine("a", 10, usage=.8), token_increment=10)
        self.assertAlmostEqual(p.token, .8)

    def test_03_new_session_uses_low_pressure(self):
        d = decision(G.GreedyStepKind.NEW_SESSION, None, [engine("a",800),engine("b",100)], [edge("a"),edge("b")])
        self.assertEqual(d.selected_target, "b")

    def test_04_hysteresis_keeps_owner(self):
        d = decision(G.GreedyStepKind.EXISTING_SESSION, "a", [engine("a",500),engine("b",490)], [edge("a"),edge("b")])
        self.assertEqual(d.selected_target, "a")
        self.assertFalse(d.threshold_met)

    def test_05_migration_above_threshold(self):
        d = decision(G.GreedyStepKind.EXISTING_SESSION, "a", [engine("a",900),engine("b",100)], [edge("a",0),edge("b",0)])
        self.assertEqual(d.selected_target, "b")
        self.assertTrue(d.threshold_met)

    def test_06_owner_wins_tie_even_at_zero_threshold(self):
        d = decision(G.GreedyStepKind.EXISTING_SESSION, "a", [engine("a"),engine("b")], [edge("a"),edge("b")], 0)
        self.assertEqual(d.selected_target, "a")

    def test_07_failover_bypasses_hysteresis(self):
        d = decision(G.GreedyStepKind.MANDATORY_FAILOVER, "dead", [engine("a",500),engine("b",100)], [edge("a"),edge("b")], 1)
        self.assertEqual(d.selected_target,"b")
        self.assertIsNone(d.threshold_met)

    def test_08_stable_tie_break(self):
        self.assertEqual(G.choose_stable_engine("s",["a","b","c"]), G.choose_stable_engine("s",["c","b","a"]))

    def test_09_nonfinite_pressure_rejected(self):
        with self.assertRaises(ValueError):
            engine("a", float("nan"))

    def test_10_duplicate_candidate_rejected(self):
        with self.assertRaises(ValueError):
            decision(G.GreedyStepKind.NEW_SESSION,None,[engine("a")],[edge("a"),edge("a")])

    def test_11_full_prompt_migration_can_outweigh_idle_engine(self):
        d = decision(G.GreedyStepKind.EXISTING_SESSION, "a", [engine("a",400),engine("b",0)], [edge("a",1),edge("b",1000)], 0)
        self.assertEqual(d.selected_target,"a")
        OBS["cache_locality_pressure_example"] = dict(d.candidate_projected_scores)


class TrainingProbes(unittest.TestCase):
    def test_12_anchor_advantage_broadcast_raw_sparse(self):
        ss=[sample("a",segment=0),sample("a",segment=1,reward=1),sample("b",reward=0)]
        raw, adv=R.reward_post_process(args(),ss)
        self.assertEqual(raw,[0.,1.,0.]); self.assertEqual(adv,[.5,.5,-.5])

    def test_13_parent_count_not_segment_count(self):
        ss=[sample("a",segment=i,reward=float(i==4)) for i in range(5)] + [sample("b",reward=0)]
        _,adv=R.reward_post_process(args(),ss)
        self.assertEqual(adv,[.5]*5+[-.5])

    def test_14_removed_parent_excluded_from_baseline(self):
        ss=[sample("a",reward=1),sample("b",reward=0,dead=True)]
        _,adv=R.reward_post_process(args(),ss)
        self.assertEqual(adv[0],0.)

    def test_15_optional_population_std(self):
        _,adv=R.reward_post_process(args(grpo_std_normalization=True),[sample("a",reward=1),sample("b")])
        self.assertEqual(adv,[1.,-1.])

    def test_16_no_normalization_still_broadcasts(self):
        ss=[sample("a",segment=0),sample("a",segment=1,reward=1),sample("b")]
        raw,adv=R.reward_post_process(args(rewards_normalization=False),ss)
        self.assertEqual(raw,[0.,1.,0.]); self.assertEqual(adv,[1.,1.,0.])

    def test_17_prompt_pools_multiple_trajectories(self):
        ss=[sample("a",mask=(1,1,1)),sample("a",segment=1,mask=(1,0,1)),sample("b",mask=(1,1)),sample("c",prompt="q",group=1,mask=(1,1,1,1))]
        den=C._prompt_equal_rollout_mask_sums(args(),ss,[s.loss_mask for s in ss])
        self.assertEqual(den,[3.5,3.5,3.5,2.])

    def test_18_split_invariance_of_precomputed_denominator(self):
        full=[sample("a",mask=(1,1,1,1))]
        split=[sample("a",mask=(1,1)),sample("a",segment=1,mask=(1,1))]
        d1=C._prompt_equal_rollout_mask_sums(args(),full,[s.loss_mask for s in full])
        d2=C._prompt_equal_rollout_mask_sums(args(),split,[s.loss_mask for s in split])
        self.assertEqual(d1,[1.]); self.assertEqual(d2,[1.,1.])
        self.assertEqual(4/d1[0],sum(2/d for d in d2))

    def test_19_zero_mask_live_prompt_still_counts(self):
        s=sample("a",mask=(1,1,1,1)); z=sample("z",prompt="z",group=1,mask=(0,0))
        alone=C._prompt_equal_rollout_mask_sums(args(),[s],[s.loss_mask])
        together=C._prompt_equal_rollout_mask_sums(args(),[s,z],[s.loss_mask,z.loss_mask])
        self.assertEqual(alone,[1.]); self.assertEqual(together,[2.,0.])
        OBS["zero_mask_not_removed_prompt_denominators"]={"alone":alone,"with_zero_mask_prompt":together}

    def test_20_missing_live_group_identity_rejected(self):
        s=sample("a",group=None)
        with self.assertRaises(AssertionError):
            C._prompt_equal_rollout_mask_sums(args(),[s],[s.loss_mask])

    def test_21_first_dead_sample_controls_logprob_field(self):
        dead=sample("d",prompt="d",group=1,mask=(),dead=True,logs=False)
        live=sample("a",reward=1)
        a=C.convert_samples_to_train_data(args(),copy.deepcopy([dead,live]))
        b=C.convert_samples_to_train_data(args(),copy.deepcopy([live,dead]))
        self.assertNotIn("rollout_log_probs",a)
        self.assertIn("rollout_log_probs",b)
        self.assertIsNone(b["rollout_log_probs"][1])
        OBS["mixed_batch_logprob_order_sensitivity"]={"dead_first_has_field":False,"live_first_has_field":True,"live_first_contains_none":True}

    def test_22_same_instance_different_group_denominator_coalesces(self):
        ss=[sample("a",group=0,mask=(1,1)),sample("b",group=1,mask=(1,1))]
        d=C._prompt_equal_rollout_mask_sums(args(),ss,[s.loss_mask for s in ss])
        self.assertEqual(d,[1.,1.])
        OBS["group_vs_instance_identity"]="advantage groups use group_index; denominator coalesces matching instance_id"

    def test_23_tq_and_mopd_explicitly_incompatible(self):
        s=sample("a")
        s.metadata["dressage_tq_sample_ref"]={"full_logprobs":{"fixture":True}}
        with self.assertRaisesRegex(ValueError,"cannot share"):
            C.convert_samples_to_train_data(args(mopd_teacher_config="fixture.json"),[s])

    def test_24_prompt_equal_is_not_trajectory_equal(self):
        # Algebraic reference using real denominator helper, not backend gradients.
        ss=[sample("a",mask=(1,)),sample("b",mask=(1,1,1))]
        d=C._prompt_equal_rollout_mask_sums(args(global_batch_size=2),ss,[s.loss_mask for s in ss])
        pooled=(.5/d[0]+3*(-.5)/d[1])/2
        per_trajectory=(.5+(-.5))/2
        self.assertEqual(pooled,-.25); self.assertEqual(per_trajectory,0.)
        OBS["prompt_vs_trajectory_equal_algebra"]={"prompt_pooled":pooled,"trajectory_average":per_trajectory}


    def test_25_official_failure_placeholder_empty_list_preserves_field(self):
        # fully_async_rollout._mark_no_grad_failed explicitly sets [], not None.
        # This fixture mirrors its documented output; the heavy worker is not run.
        dead=sample("d",prompt="d",group=1,mask=(),dead=True,logs=False)
        dead.rollout_log_probs=[]
        live=sample("a",reward=1)
        data=C.convert_samples_to_train_data(args(),[dead,live])
        self.assertEqual(data["rollout_log_probs"],[[],[-.5,-.5]])
        OBS["official_placeholder_avoids_none_counterexample"]=True


def main():
    global G,R,C
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    options=parser.parse_args()
    os.environ.pop("DRESSAGE_MOPD_TEACHER_CONFIG",None)
    (G,R,C),hashes=load_sources(options.source_root)
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(RoutingProbes),unittest.defaultTestLoader.loadTestsFromTestCase(TrainingProbes)])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={"source_commit":PIN,"git_blob_hashes":hashes,"python":platform.python_version(),
            "scope":"CPU functions only; explicit Sample doubles and transport-key stub; no Ray, GPU, SGLang, sandbox, or full upstream suite",
            "tests_run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),
            "success":result.wasSuccessful(),"observations":OBS}
    options.output.parent.mkdir(parents=True,exist_ok=True)
    options.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return 0 if result.wasSuccessful() else 1

if __name__=="__main__":
    raise SystemExit(main())
