"""训练侧算法参考层（FA-4 起）：faithful DIS 对拍权威等。

与 adapters/ 的边界：adapters 负责与具体后端的数据交接（形状/契约），
training/ 负责与后端无关的算法数值语义（loss/梯度/指标的参考实现）。
"""
