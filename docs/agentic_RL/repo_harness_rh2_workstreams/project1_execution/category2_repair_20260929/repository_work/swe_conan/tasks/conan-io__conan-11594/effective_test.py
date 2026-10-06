import platform
import pytest

from conan.tools.cmake import CMake
from conan.tools.cmake.presets import write_cmake_presets
from conans.client.conf import get_default_settings_yml
from conans.model.conf import Conf
from conans.model.settings import Settings
from conans.test.utils.mocks import ConanFileMock
from conans.test.utils.test_files import temp_folder


@pytest.mark.parametrize("generator,target", [
    ("NMake Makefiles", "test"),
    ("Ninja Makefiles", "test"),
    ("Ninja Multi-Config", "test"),
    ("Unix Makefiles", "test"),
    ("Visual Studio 14 2015", "RUN_TESTS"),
    ("Xcode", "RUN_TESTS"),
])
def test_run_tests(generator, target):
    """
    Testing that the proper test target is picked for different generators, especially multi-config ones.
    Issue related: https://github.com/conan-io/conan/issues/11405
    """
    settings = Settings.loads(get_default_settings_yml())
    settings.os = "Windows"
    settings.arch = "x86"
    settings.build_type = "Release"
    settings.compiler = "Visual Studio"
    settings.compiler.runtime = "MDd"
    settings.compiler.version = "14"

    conanfile = ConanFileMock()
    conanfile.conf = Conf()
    conanfile.folders.generators = "."
    conanfile.folders.set_base_generators(temp_folder())
    conanfile.settings = settings

    write_cmake_presets(conanfile, "toolchain", generator, {})
    cmake = CMake(conanfile)
    cmake.test()

    search_pattern = "--target {}" if platform.system() == "Windows" else "'--target' '{}'"
    assert search_pattern.format(target) in conanfile.command


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
