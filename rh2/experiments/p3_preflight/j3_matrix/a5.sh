#!/bin/bash
# J3 主轴 A · A5：CP=2 降档（协议："任一 · CP=2，仅当 32k 显存不够时启用"）。
# 本文件把 CP2 施加在 A2 的 4 卡基座上：TP2×CP2×DP1 · EP4·ETP1。
# max-tokens-per-gpu 由 run_j3.sh 按 CTX/CP 自动算（J3 附②长上下文三件套）。
J3_NAME=a5
J3_TRAIN_GPUS=4
J3_TP=2
J3_PP=1
J3_CP=2
J3_DP=1
J3_EP=4
J3_ETP=1
