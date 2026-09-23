# 公开开发检查（来源：quality_batch01 cpu_queue.json 的 actor-dvc5839 command_draft；只含公开内容）。
# 先记不注入 PYTHONPATH 时的导入来源，再按草案显式 PYTHONPATH=/testbed 跑 CLI。
step() { echo "=== STEP $1"; shift; "$@"; echo "=== RC $?"; }
step import_plain python -c 'import sys,dvc; from dvc.command.metrics import _show_metrics; print(sys.executable,sys.version,dvc.__file__)'
step import_from_tmp bash -c 'cd /tmp && python -c "import dvc; print(dvc.__file__)"'
cli() {
  d=$(mktemp -d)
  printf 'mae: 1.4832495253358502e-05\nmse: 5.0172572763074186e-09\n' > "$d/metrics.yaml"
  ( cd "$d"
    for extra in "" "--precision 4" "--precision 8" "--precision 8 --show-md" "--precision 8 --show-json"; do
      echo "--- dvc metrics show metrics.yaml $extra"
      DVC_TEST=true PYTHONPATH=/testbed python -m dvc metrics show metrics.yaml $extra; echo "--- rc=$?"
    done )
  rm -rf "$d"
}
step cli_matrix cli
step narrow_tests env DVC_TEST=true python -m pytest -q tests/unit/command/test_metrics.py::test_metrics_show_precision tests/unit/command/test_metrics.py::test_metrics_diff_precision
step git_status git status --porcelain
