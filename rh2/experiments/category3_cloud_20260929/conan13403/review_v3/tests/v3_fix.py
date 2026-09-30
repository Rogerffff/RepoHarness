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
    otherwise the current folder. It does not run anything. ``run_error`` simulates a failing
    command: like ConanFile.run, it is raised, or with ``ignore_errors=True`` a non-zero exit
    code is returned instead."""

    def __init__(self):
        super().__init__()
        self.runs = []
        self.run_error = None
        self.failed_codes_returned = 0

    def run(self, command, stdout=None, cwd=None, ignore_errors=False, **kwargs):
        folder = cwd if cwd else os.getcwd()
        if not os.path.isdir(folder):
            raise ConanException("Error while running cmd\nError: {} not found".format(folder))
        self.command = command
        self.runs.append((os.path.realpath(folder), command))
        if self.run_error is not None:
            if ignore_errors:
                self.failed_codes_returned += 1
                return 1
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

        # The current folder of the caller is restored, also when it is not the build folder
        os.chdir(root)
        autotools.autoreconf(build_script_folder="subfolder")
        assert conanfile.runs[-1] == (real(subfolder), 'autoreconf -bar foo')
        assert real(os.getcwd()) == real(root)
        os.chdir(build)

        # A failing autoreconf is not hidden: an error is raised (any type and message), the
        # failing command ran once, only in the selected folder, and the current folder of the
        # caller is restored (here the caller is not in the build folder)
        conanfile.run_error = ConanException("autoreconf failed")
        os.chdir(root)
        before = len(conanfile.runs)
        with pytest.raises(Exception):
            autotools.autoreconf(build_script_folder="subfolder")
        assert conanfile.runs[before:] == [(real(subfolder), 'autoreconf -bar foo')]
        assert real(os.getcwd()) == real(root)
    finally:
        os.chdir(folder)
