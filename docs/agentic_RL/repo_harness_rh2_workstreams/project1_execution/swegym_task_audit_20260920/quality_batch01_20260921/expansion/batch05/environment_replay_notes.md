# 第五批环境入口（内部静态材料）

原条件与文件hash见 [environment_replay_inventory.json](environment_replay_inventory.json)。只服务私有协调，不给公开读者，不构成执行授权。

- **mypy11707**：原`install_wave1`派生镜像，原baseline代码归档CLI，显式传本题`--derived-image`和`--derived-image-recipe`；离线wheel pins按本题plan。无recipe/materials/reference bindings覆写。
- **Moto5406**：原`baseline01`，使用原镜像tag与账本记录的manifest digest；`image_id_actual`原账本为null，不能补填派生镜像或本地ID。原入口是campaign/worker调用默认ReplayGrader；清单按精确instance_id定位worker jobs和events。无覆写。

两题原grader/spec版本、完整测试命令及noop/gold证据分别记录。Moto base的Terraform provider gitlink只有固定commit，内容未导出；是否存在于实际镜像仍未知。summary仍引用原/work路径，目标机镜像、代码环境和重定位summary均待准备。mypy的image.json是构建审计；若原派生镜像不存在，需要真实wheel/context，不能把审计输出当输入。历史ledger/audit不作新运行输出位置。
