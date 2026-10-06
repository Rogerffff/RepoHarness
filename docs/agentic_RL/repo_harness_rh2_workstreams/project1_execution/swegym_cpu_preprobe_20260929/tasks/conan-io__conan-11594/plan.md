# Conan11594 CPU接续

已准备、未执行。公开输入实际使用TestClient建立无外部依赖recipe，经CMakeToolchain生成Ninja Multi-Config，再调用新CMake helper真实test；CTest检查Release并写marker。base目标失败不能由mock或缺工具代替。公开旧测试单独运行。

恢复该题原manifest、baseline安装及reference_v1的Ninja完整node绑定；不是Conan15422配方。只有工具实测缺失时才考虑recovery.json候选pin，此pin为新建议尚未验证。私有丢配置候选同时保留正确target，用正式评分及真实CTest区分。

剩余：实际工具版本/actor权限、公开运行与全部失败归因、noop/gold/退化评分、独立复核。当前只作问题定位；能力比较与训练均conditional；未批准GPU或训练。

本次可执行恢复入口为同题 `task_inputs/conan-io__conan-11594/buildplan.json`（具体脚本与调用参数见该文件）。`evidence_sources.json` 保存既有题卡、公开读者、复核和材料原件的路径及SHA。私有 `patch_validation.json` 已记录每个补丁在base临时副本上的真实应用前后哈希与AST检查；它不代表远端投影或功能验证，远端仍需核最终应用字节。
