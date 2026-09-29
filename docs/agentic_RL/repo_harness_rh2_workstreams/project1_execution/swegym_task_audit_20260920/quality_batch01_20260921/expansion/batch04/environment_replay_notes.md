# 第四批原环境入口（内部材料，未执行）

仅为固定3题整理静态入口；不评质量、不交公开读者。逐题镜像ID、测试命令/spec版本、原输入与审计输出hash见 [environment_replay_inventory.json](environment_replay_inventory.json)。

- **DVC4185**：`dvc_install_v1c`派生镜像，必须同时传该批wrapper的`--recipe recipes/iterative__dvc-4185.json`和`--bindings reference_bindings_v1.json`，并保留同目录`reference_bindings.py`。安装覆写包含`networkx==2.3+rh2.1`和`.[all,tests]`；grader有`+reference-bindings-v1`。使用DVC源码归档。
- **mypy16869**：`install_wave1`派生镜像、baseline源码归档的原CLI；使用本题Python3.12及本题wheel pins，无recipe/materials/bindings覆写。
- **Moto6114**：同属`install_wave1`，使用本题镜像和pins，原CLI无覆写。base内Terraform provider gitlink只有固定commit，未导出内容；不据此推断实际镜像中子模块是否存在。

DVC的批次`recipes/<id>.json`和带顶层`tasks`的bindings文件是输入；各run的`recipe/recipe.json`、`recipe/reference_bindings.json`和before/after脚本是审计输出，不能互换。已对拍两份recipe审计及两份bindings审计。`networkx_backport.json`只证明原自定义wheel的构建记录，不是wheel本体。三题都未使用`--materials`。

共同CLI参数已集中列在清单；原资源为2 CPU/4 GiB/PID512、deny_all，candidate应用身份agent/54321、grader身份rh2grader/54322。目标运行机镜像可用性仍待核；原summary副本指向旧/work目录，运行前须另备重定位summary及代码环境。三个原context/wheel payload不在本地副本中；镜像缺失时须按本题pins和构建审计补准备。不得覆写原ledger/audit；本清单不是执行授权。
