# 测试段（第二个 exec，宿主在断网核对后才启动）：只 source 候选自己写的状态文件
set -u
. "$1/rh2_env.sh"; . "$1/rh2_funcs.sh"; cd "$(cat "$1/rh2_cwd")"
echo "OMP=$OMP_NUM_THREADS MKL=$MKL_NUM_THREADS PATH_HEAD=${PATH%%:*} CWD=$(pwd) FUNC=$(myfunc) NOT_EXPORTED=${NOT_EXPORTED:-absent}"
