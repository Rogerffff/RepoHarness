# Dask7305 题级评分环境恢复建议；当前只是资产，尚未部署或验证。
# 在新评分进程启动前应用，且位于环境激活及安装携带状态恢复之后。
# 不改候选、测试断言、scheduler、进程池显式参数或资源上限。
export DASK_NUM_WORKERS=2
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
