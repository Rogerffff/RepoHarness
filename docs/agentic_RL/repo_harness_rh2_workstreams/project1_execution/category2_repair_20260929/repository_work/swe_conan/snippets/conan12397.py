

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
