# 本题开发环境说明

公开base位于`/testbed`，`python`使用已激活testbed环境；Conan从本仓源码导入，源码版本为1.54.0-dev。原issue中的1.53.0描述提交者环境。

公开Meson工具链可以通过`python -m conans.conan install`生成配置文件，在本机查看。现有检查覆盖配置生成和仓库已有测试；clang／Meson／libc++的完整编译与链接路径尚未验证。
