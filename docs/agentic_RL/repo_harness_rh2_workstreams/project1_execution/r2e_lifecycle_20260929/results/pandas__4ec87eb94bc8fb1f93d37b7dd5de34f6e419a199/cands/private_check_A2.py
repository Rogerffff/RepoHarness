import pandas as pd
a = pd.array([1, None, 3], dtype="Int64").astype("Float64")
print("astype data/mask", a._data, a._mask)                      # 预计 [1. 1. 3.] [False  True False]
print("astype", pd.Series(a).groupby([0, 0, 0]).quantile(0.5).tolist())    # gold [2.0]；C0 预计 [1.0]
b = pd.Series([2.5], dtype="Float64").reindex([0, 1])
print("reindex data/mask", b.array._data, b.array._mask)         # 预计 [2.5 0. ] [False  True]
print("reindex", b.groupby([1, 1]).quantile(0.5).tolist())                  # gold [2.5]；C0 预计 [0.0]
c = pd.array([1, None, 3], dtype="Int64") / 1
print("div data", c._data)                                        # 预计 [1. 1. 3.]
print("div", pd.Series(c).groupby([0, 0, 0]).quantile(0.5).tolist())       # gold [2.0]；C0 预计 [1.0]
