# 来源、harness 与观测口径

旧：Pro s12 / Flash s15；新：Pro s23 / Flash s30。缺失不前值填充；匿名 ID 不推定实际数据集或产品。

## 各来源平均 response 长度

| 来源 | Pro 旧 | Pro 新 | Flash 旧 | Flash 新 |
| --- | ---: | ---: | ---: | ---: |
| chat/dataset-8kb6 | 8054.64 | 6126.26 | 4505.46 | 6056.21 |
| chat/dataset-eup7 | 2639.83 | 2151.79 | 2597.27 | 3282.29 |
| chat/dataset-lm3t | 1246.18 | 2505.75 | 3917.08 | 18976.6 |
| code/dataset-4onq | 40130.2 | 50074.2 | 52505.2 | 62024.4 |
| code/dataset-bvg7 | 92677.6 | 107491 | 90075.8 | 148781 |
| code/dataset-dnpn | 51511.1 | 69590 | 53411.3 | 84334.2 |
| code/dataset-m1dt | 62424.4 | 83541.5 | 74474.6 | 106590 |
| code/dataset-obg8 | 109551 | 139134 | 112931 | 160332 |
| code/dataset-sin0 | 89523.2 | 118132 | 106034 | 148263 |
| code/dataset-ta4j | 110128 | 125560 | 103200 | 140479 |
| code/dataset-v7yx | 85928 | 99394.4 | 79895.9 | 123170 |
| code/dataset-x7wh | 106591 | 133858 | 111816 | 153168 |
| code/dataset-yfch | 262637 | 298450 | 440762 | 524848 |
| code/dataset-zg6q | 52787.7 | 73633.4 | 60598.9 | 92293.8 |
| cyber/dataset-9aui | 228349 | — | 233262 | 342206 |
| general/dataset-1doa | 65261.2 | 68955.4 | 83765.1 | 97361.9 |
| general/dataset-5610 | 70133.6 | 79851.6 | 70869.5 | 127438 |
| general/dataset-epqd | 61208.6 | 58451.8 | 63754.1 | 93475.3 |
| general/dataset-trla | 64391 | 65490.6 | 80689.6 | 98000.2 |
| visual/dataset-053e | 95707.6 | 114475 | 107432 | 135511 |
| visual/dataset-gtav | 29185.7 | 37874.2 | 39288 | 45011 |
| visual/dataset-jzd3 | 27924.3 | 35756 | 34561.2 | 46963.2 |
| visual/dataset-ol8x | 87855.3 | 108806 | 100286 | 131097 |
| visual/dataset-pt5v | 96908.8 | 150896 | 142711 | 203166 |
| visual/dataset-ve5o | 140446 | 197011 | 188418 | 270730 |

## 当前 step 的 harness rollouts 与非零 advantage 比率

rollouts 的求和不是 25,088；公开资料未解释两个统计分母的差异，不擅自认定是过滤率。
网页 Pro s23 表格中的 harness-R=1,022 是 s14 的最后一次记录；s15–23 缺失。表格由 lastOf 聚合，柱图则把空值视为 0，二者不能混读。

| harness | Pro rollouts | Pro 非零 ADV | Flash rollouts | Flash 非零 ADV |
| --- | ---: | ---: | ---: | ---: |
| harness-A | 4725 | 0.969524 | 3487 | 0.990823 |
| harness-A-pw | 160 | 1 | 176 | 1 |
| harness-B | 2992 | 0.97861 | 3549 | 0.977458 |
| harness-C | 3440 | 0.972093 | 3628 | 0.960584 |
| harness-D | 2846 | 0.966268 | 3255 | 0.975422 |
| harness-D-pw | 160 | 0.9125 | 176 | 1 |
| harness-E | 368 | 1 | 544 | 1 |
| harness-F | 656 | 1 | 496 | 1 |
| harness-G-pw | 304 | 1 | 141 | 0.992908 |
| harness-H | 2457 | 0.998779 | 2468 | 1 |
| harness-I | 95 | 1 | 108 | 1 |
| harness-J | 208 | 1 | 239 | 1 |
| harness-K | 144 | 1 | 111 | 1 |
| harness-L | 112 | 1 | 144 | 1 |
| harness-M | 208 | 1 | 191 | 1 |
| harness-N | 175 | 1 | 160 | 1 |
| harness-O | 160 | 1 | 160 | 1 |
| harness-P | 384 | 1 | 176 | 1 |
| harness-Q | 112 | 1 | 158 | 1 |
| harness-R | — | — | 1023 | 1 |
| harness-S | 496 | 1 | 496 | 1 |
| harness-T | 1024 | 1 | 1039 | 1 |
| harness-U | 496 | 1 | 496 | 1 |

## 最新数据源构成（复算网页近似算法）

| 类别 | Pro s23（重启后按比例近似） | Flash s30（池计数推导） |
| --- | ---: | ---: |
| code | 69.376% | 67.411% |
| general | 11.354% | 12.245% |
| cyber | 0.000% | 4.082% |
| visual | 15.587% | 13.265% |
| chat | 3.682% | 2.997% |
