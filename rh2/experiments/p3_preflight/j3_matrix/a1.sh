#!/bin/bash
# J3 主轴 A · A1：2 卡 · TP2×DP1 · EP2·ETP1（T2′ 训练侧形态）。
# 协议原文：必测——决定 rollout-heavy（2 训 + 6 推）是否被训练步反噬。
# 校验不变量（tests/check_p3_scripts.py 静态断言）：
#   TP×CP×PP×DP == J3_TRAIN_GPUS；EP×ETP 整除 J3_TRAIN_GPUS；128 % EP == 0。
J3_NAME=a1
J3_TRAIN_GPUS=2
J3_TP=2
J3_PP=1
J3_CP=1
J3_DP=1
J3_EP=2
J3_ETP=1
