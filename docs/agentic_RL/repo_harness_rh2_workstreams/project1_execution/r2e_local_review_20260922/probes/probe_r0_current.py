"""在当前树重跑 09-20 原始 R-0 审查探针，保留历史脚本和结果不变。

运行：rh2/.venv/bin/python <本文件> > <本次结果路径>
使用固定 profile 和 Docker I/O 替身；另含缺补丁的真实 CLI 子进程（不会启动容器）。
"""
from pathlib import Path
import runpy

execution = Path(__file__).resolve().parents[2]
runpy.run_path(str(execution / "r2e_grading_wiring_review_20260920/probe_r0_followup.py"), run_name="__main__")
