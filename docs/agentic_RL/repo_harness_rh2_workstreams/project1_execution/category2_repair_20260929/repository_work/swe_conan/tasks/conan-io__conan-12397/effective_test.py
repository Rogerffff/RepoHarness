import sys
import textwrap

import pytest

from conan.tools.meson import MesonToolchain
from conans.test.utils.tools import TestClient


@pytest.mark.skipif(sys.version_info.major == 2, reason="Meson not supported in Py2")
def test_apple_meson_keep_user_custom_flags():
    default = textwrap.dedent("""
    [settings]
    os=Macos
    arch=x86_64
    compiler=apple-clang
    compiler.version=12.0
    compiler.libcxx=libc++
    build_type=Release
    """)

    cross = textwrap.dedent("""
    [settings]
    os = iOS
    os.version = 10.0
    os.sdk = iphoneos
    arch = armv8
    compiler = apple-clang
    compiler.version = 12.0
    compiler.libcxx = libc++

    [conf]
    tools.apple:sdk_path=/my/sdk/path
    """)

    _conanfile_py = textwrap.dedent("""
    from conan import ConanFile
    from conan.tools.meson import MesonToolchain

    class App(ConanFile):
        settings = "os", "arch", "compiler", "build_type"

        def generate(self):
            tc = MesonToolchain(self)
            # Customized apple flags
            tc.apple_arch_flag = ['-arch', 'myarch']
            tc.apple_isysroot_flag = ['-isysroot', '/other/sdk/path']
            tc.apple_min_version_flag = ['-otherminversion=10.7']
            tc.generate()
    """)

    t = TestClient()
    t.save({"conanfile.py": _conanfile_py,
            "build_prof": default,
            "host_prof": cross})

    t.run("install . -pr:h host_prof -pr:b build_prof")
    content = t.load(MesonToolchain.cross_filename)
    assert "c_args = ['-isysroot', '/other/sdk/path', '-arch', 'myarch', '-otherminversion=10.7']" in content
    assert "c_link_args = ['-isysroot', '/other/sdk/path', '-arch', 'myarch', '-otherminversion=10.7']" in content
    for key in ("cpp_args", "cpp_link_args"):
        args = _rh2_meson_args(content, key)
        assert "-stdlib=libc++" in args
        assert "-otherminversion=10.7" in args
        for pair in (["-isysroot", "/other/sdk/path"], ["-arch", "myarch"]):
            assert any(args[i:i + 2] == pair for i in range(len(args) - 1))


@pytest.mark.skipif(sys.version_info.major == 2, reason="Meson not supported in Py2")
def test_extra_flags_via_conf():
    profile = textwrap.dedent("""
        [settings]
        os=Windows
        arch=x86_64
        compiler=gcc
        compiler.version=9
        compiler.cppstd=17
        compiler.libcxx=libstdc++
        build_type=Release

        [buildenv]
        CFLAGS=-flag0 -other=val
        CXXFLAGS=-flag0 -other=val
        LDFLAGS=-flag0 -other=val

        [conf]
        tools.build:cxxflags=["-flag1", "-flag2"]
        tools.build:cflags=["-flag3", "-flag4"]
        tools.build:sharedlinkflags+=["-flag5"]
        tools.build:exelinkflags+=["-flag6"]
   """)
    t = TestClient()
    t.save({"conanfile.txt": "[generators]\nMesonToolchain",
            "profile": profile})

    t.run("install . -pr=profile")
    content = t.load(MesonToolchain.native_filename)
    assert "cpp_args = ['-flag0', '-other=val', '-flag1', '-flag2', '-D_GLIBCXX_USE_CXX11_ABI=0']" in content
    assert "c_args = ['-flag0', '-other=val', '-flag3', '-flag4']" in content
    assert "c_link_args = ['-flag0', '-other=val', '-flag5', '-flag6']" in content
    assert "cpp_link_args = ['-flag0', '-other=val', '-flag5', '-flag6']" in content


@pytest.mark.skipif(sys.version_info.major == 2, reason="Meson not supported in Py2")
def test_correct_quotes():
    profile = textwrap.dedent("""
       [settings]
       os=Windows
       arch=x86_64
       compiler=gcc
       compiler.version=9
       compiler.cppstd=17
       compiler.libcxx=libstdc++11
       build_type=Release
       """)
    t = TestClient()
    t.save({"conanfile.txt": "[generators]\nMesonToolchain",
            "profile": profile})

    t.run("install . -pr=profile")
    content = t.load(MesonToolchain.native_filename)
    assert "cpp_std = 'c++17'" in content
    assert "backend = 'ninja'" in content
    assert "buildtype = 'release'" in content


def _rh2_meson_args(content, key):
    # 读取完整 INI 键；安全解释列表/常量/拼接，避免 objcpp 后缀碰撞和引号约束。
    import ast
    import configparser

    ini = configparser.RawConfigParser()
    ini.read_string(content)
    resolving = set()

    def read(node):
        if isinstance(node, ast.List):
            return [read(element) for element in node.elts]
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = read(node.left), read(node.right)
            assert isinstance(left, list) and isinstance(right, list)
            return left + right
        if isinstance(node, ast.Name):
            assert node.id not in resolving, "cyclic Meson constant"
            resolving.add(node.id)
            try:
                return read(ast.parse(ini.get("constants", node.id), mode="eval").body)
            finally:
                resolving.remove(node.id)
        raise AssertionError("unsupported Meson argument expression: " + ast.dump(node))

    value = read(ast.parse(ini.get("built-in options", key), mode="eval").body)
    assert isinstance(value, list) and all(isinstance(item, str) for item in value)
    return value


def test_linux_native_clang_libcxx_link_args():
    profile = textwrap.dedent("""
        [settings]
        os=Linux
        arch=x86_64
        compiler=clang
        compiler.version=14
        compiler.libcxx=libc++
        build_type=Release
    """)
    client = TestClient()
    client.save({"conanfile.txt": "[generators]\nMesonToolchain", "profile": profile})
    client.run("install . -pr:h=profile -pr:b=profile")
    content = client.load(MesonToolchain.native_filename)
    assert "-stdlib=libc++" in _rh2_meson_args(content, "cpp_args")
    assert "-stdlib=libc++" in _rh2_meson_args(content, "cpp_link_args")
