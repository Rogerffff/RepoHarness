import os

import pytest

from conan.tools.build import save_toolchain_args
from conan.tools.gnu import Autotools
from conans.errors import ConanException
from conans.test.utils.mocks import ConanFileMock
from conans.test.utils.test_files import temp_folder
from conans.util.files import save


class _RunRecorderConanFile(ConanFileMock):
    """Records the folder where each command would run, like ConanFile.run: ``cwd`` if given,
    otherwise the current folder. It does not run anything; ``run_error`` simulates a command
    failure, which ConanFile.run reports with a ConanException."""

    def __init__(self):
        super().__init__()
        self.runs = []
        self.run_error = None

    def run(self, command, stdout=None, cwd=None, **kwargs):
        folder = cwd if cwd else os.getcwd()
        if not os.path.isdir(folder):
            raise FileNotFoundError(folder)
        self.command = command
        self.runs.append((os.path.realpath(folder), command))
        if self.run_error is not None:
            raise self.run_error
        return 0


def test_source_folder_works():
    folder = temp_folder()
    os.chdir(folder)
    save_toolchain_args({
        "configure_args": "-foo bar",
        "make_args": "",
        "autoreconf_args": "-bar foo"}
    )
    conanfile = ConanFileMock()
    sources = "/path/to/sources"
    conanfile.folders.set_base_source(sources)
    autotools = Autotools(conanfile)
    autotools.configure(build_script_folder="subfolder")
    assert conanfile.command.replace("\\", "/") == '"/path/to/sources/subfolder/configure" -foo bar '

    autotools = Autotools(conanfile)
    autotools.configure()
    assert conanfile.command.replace("\\", "/") == '"/path/to/sources/configure" -foo bar '

    # autoreconf runs in the selected folder, with real folders that contain a configure.ac:
    # by default the source folder, a folder relative to the source folder, or an absolute
    # folder such as the build folder or another absolute path
    root = temp_folder()
    source = os.path.join(root, "source")
    subfolder = os.path.join(source, "subfolder")
    build = os.path.join(root, "build")
    for f in (source, subfolder, build):
        save(os.path.join(f, "configure.ac"), "")
    conanfile = _RunRecorderConanFile()
    conanfile.folders.set_base_source(source)
    conanfile.folders.set_base_build(build)
    conanfile.folders.set_base_generators(folder)
    autotools = Autotools(conanfile)
    real = os.path.realpath
    os.chdir(build)  # the recipe build() method runs in the build folder
    try:
        calls = [({}, source, 'autoreconf -bar foo'),
                 ({"build_script_folder": "subfolder"}, subfolder, 'autoreconf -bar foo'),
                 ({"build_script_folder": conanfile.build_folder, "args": ["--install"]}, build,
                  'autoreconf -bar foo --install'),
                 ({"build_script_folder": subfolder}, subfolder, 'autoreconf -bar foo'),
                 ({}, source, 'autoreconf -bar foo')]
        for kwargs, expected_folder, expected_command in calls:
            before = len(conanfile.runs)
            autotools.autoreconf(**kwargs)
            assert conanfile.runs[before:] == [(real(expected_folder), expected_command)], kwargs
            # the current folder of the caller and the recipe folders are not changed
            assert real(os.getcwd()) == real(build), kwargs
            assert conanfile.source_folder == source
            assert conanfile.build_folder == build

        # A selected folder that does not exist is an error; autoreconf is not run elsewhere
        before = len(conanfile.runs)
        with pytest.raises(Exception):
            autotools.autoreconf(build_script_folder="missing")
        assert len(conanfile.runs) == before
        assert real(os.getcwd()) == real(build)

        # A failing autoreconf is not hidden, and the current folder is restored
        conanfile.run_error = ConanException("autoreconf failed")
        with pytest.raises(Exception, match="autoreconf failed"):
            autotools.autoreconf(build_script_folder="subfolder")
        assert real(os.getcwd()) == real(build)
    finally:
        os.chdir(folder)
