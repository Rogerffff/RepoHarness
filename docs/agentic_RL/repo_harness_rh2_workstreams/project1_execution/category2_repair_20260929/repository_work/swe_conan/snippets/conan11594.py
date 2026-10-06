

def test_ninja_multiconfig_executes_requested_release():
    # 复用已验公开流程，实际执行 CTest；仅测试目标为 NONE，不引入编译器要求。
    from conans.test.utils.tools import TestClient

    client = TestClient()
    recipe = '''from conan import ConanFile
from conan.tools.cmake import CMake
class ReleaseTest(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"
    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.test()
'''
    cmakelists = '''cmake_minimum_required(VERSION 3.17)
project(ReleaseTest NONE)
enable_testing()
add_test(NAME requested_config COMMAND "${CMAKE_COMMAND}"
  "-DACTUAL_CONFIG=$<CONFIG>"
  "-DMARKER=${CMAKE_CURRENT_BINARY_DIR}/requested-config.txt"
  -P "${CMAKE_CURRENT_SOURCE_DIR}/check.cmake")
'''
    check = '''if(NOT ACTUAL_CONFIG STREQUAL "Release")
  message(FATAL_ERROR "Expected Release; got ${ACTUAL_CONFIG}")
endif()
file(WRITE "${MARKER}" "RELEASE_TEST_EXECUTED")
'''
    client.save({"conanfile.py": recipe, "CMakeLists.txt": cmakelists, "check.cmake": check})
    client.run('install . -s build_type=Release '
               '-c tools.cmake.cmaketoolchain:generator="Ninja Multi-Config"')
    client.run('build .')
    assert client.load("requested-config.txt") == "RELEASE_TEST_EXECUTED"
