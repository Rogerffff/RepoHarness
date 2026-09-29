# 安装段（候选 shell）：真实配方形态的 export + cd + 函数；结束时把可携带状态落到候选自己的文件
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PATH="/opt/fake/bin:$PATH"
NOT_EXPORTED=hidden
cd /tmp
myfunc() { echo "func-$OMP_NUM_THREADS"; }
export -p > "$1/rh2_env.sh"; declare -f > "$1/rh2_funcs.sh"; pwd > "$1/rh2_cwd"
echo INSTALL_DONE
