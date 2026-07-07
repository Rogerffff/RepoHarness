#!/bin/bash
# J3 主轴 A · A4：8 卡 · TP4×CP2 · EP8（slime 官方 30B 测试同款，T1 对照）。
# 参照锚：reference/slime/tests/test_qwen3_30B_A3B.py:55 起的 perf_args
# （TP4 / CP2 / EP8 / ETP1 / max-tokens-per-gpu 16384 = 32768/CP2）。
J3_NAME=a4
J3_TRAIN_GPUS=8
J3_TP=4
J3_PP=1
J3_CP=2
J3_DP=1
J3_EP=8
J3_ETP=1
