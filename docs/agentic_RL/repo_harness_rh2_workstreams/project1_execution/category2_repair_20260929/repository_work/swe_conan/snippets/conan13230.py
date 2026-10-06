

@pytest.mark.parametrize("sdk_path", [None, "/public-diagnostic-sdk"], ids=["no_sdk", "sdk_sentinel"])
def test_linux_host_from_macos_has_no_apple_cflags(sdk_path, monkeypatch):
    # 公开最小 recipe 只有 os/arch；核最终 flags，而非内部 Apple 属性的表示。
    import shlex

    # 环境会继承调用者的 CFLAGS；排除宿主遗留值，只检验当前工具链生成行为。
    monkeypatch.delenv("CFLAGS", raising=False)
    conanfile = ConanFileMock()
    conanfile.settings = MockSettings({"os": "Linux", "arch": "x86_64"})
    conanfile.settings_build = MockSettings({"os": "Macos", "arch": "armv8"})
    if sdk_path is not None:
        conanfile.conf.define("tools.apple:sdk_path", sdk_path)
    toolchain = AutotoolsToolchain(conanfile)
    assert toolchain.cflags == []
    # 环境导出必须与同一公开 cflags 一致，不安装真实 SDK 或交叉编译器。
    assert shlex.split(toolchain.vars()["CFLAGS"]) == []
