#!/bin/bash
# J3 主轴 A · A3：6 卡 · TP2×DP3 · EP2·ETP1（回退候选：仅当 A1/A2 step 过慢）。
# 注意 EP2 不等于卡数：EP×ETP=2 整除 6 即可（EP 组内 2 卡分 128 专家）。
J3_NAME=a3
J3_TRAIN_GPUS=6
J3_TP=2
J3_PP=1
J3_CP=1
J3_DP=3
J3_EP=2
J3_ETP=1
