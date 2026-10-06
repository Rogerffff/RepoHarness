环境已准备好。Claude Code启动路径会激活`/opt/miniconda3/envs/testbed`；在`/testbed`中使用`python -m mypy`和`python -m pytest`。当前mypy源码从`/testbed/mypy/`导入。依赖已可用，不需要联网安装。

可以把题面的复现代码放在临时目录，使用`python -m mypy --no-strict-optional --strict-equality <文件>`查看诊断。mypy退出1表示报告了类型错误，应结合实际诊断判断，不把它自动当成环境故障。

公开的相关成员检查测试可以这样运行：

```bash
python -m pytest -n 2 -q --color=no -p no:cacheprovider mypy/test/testcheck.py -k 'StrictEqualityWithFixedLengthTupleInCheck'
```

镜像初态的`test-requirements.txt`已有环境准备改动；这不是本次待修复的源码变更。
