import copy
import os

import patch_ng
import pytest

from conan.tools.files import patch, apply_conandata_patches
from conans.errors import ConanException
from conans.test.utils.mocks import ConanFileMock, RedirectedTestOutput
from conans.test.utils.tools import redirect_output


class MockPatchset:
    filename = None
    string = None
    apply_args = None

    def apply(self, root, strip, fuzz):
        self.apply_args = (root, strip, fuzz)
        return True


@pytest.fixture
def mock_patch_ng(monkeypatch):
    mock = MockPatchset()

    def mock_fromfile(filename):
        mock.filename = filename
        return mock

    def mock_fromstring(string):
        mock.string = string
        return mock

    monkeypatch.setattr(patch_ng, "fromfile", mock_fromfile)
    monkeypatch.setattr(patch_ng, "fromstring", mock_fromstring)
    return mock


def test_single_patch_file(mock_patch_ng):
    conanfile = ConanFileMock()
    conanfile.folders.set_base_source("/my_source")
    conanfile.folders.set_base_export_sources("/my_source")
    conanfile.display_name = 'mocked/ref'
    patch(conanfile, patch_file='patch-file')
    assert mock_patch_ng.filename.replace("\\", "/") == '/my_source/patch-file'
    assert mock_patch_ng.string is None
    assert mock_patch_ng.apply_args == ("/my_source", 0, False)


def test_single_patch_file_from_forced_build(mock_patch_ng):
    conanfile = ConanFileMock()
    conanfile.folders.set_base_source("/my_source")
    conanfile.folders.set_base_export_sources("/my_source")
    conanfile.display_name = 'mocked/ref'
    patch(conanfile, patch_file='/my_build/patch-file')
    assert mock_patch_ng.filename == '/my_build/patch-file'
    assert mock_patch_ng.string is None
    assert mock_patch_ng.apply_args == ("/my_source", 0, False)


def test_base_path(mock_patch_ng):
    conanfile = ConanFileMock()
    conanfile.folders.set_base_source("my_source")
    conanfile.folders.set_base_export_sources("my_source")
    conanfile.folders.source = "src"  # This not applies to find the patch file but for applying it
    conanfile.display_name = 'mocked/ref'
    patch(conanfile, patch_file='patch-file', base_path="subfolder")
    assert mock_patch_ng.filename.replace("\\", "/") == 'my_source/patch-file'
    assert mock_patch_ng.string is None
    assert mock_patch_ng.apply_args == (os.path.join("my_source", "src", "subfolder"), 0, False)


def test_apply_in_build_from_patch_in_source(mock_patch_ng):
    conanfile = ConanFileMock()
    conanfile.folders.set_base_source("/my_source")
    conanfile.folders.set_base_export_sources("/my_source")
    conanfile.display_name = 'mocked/ref'
    patch(conanfile, patch_file='patch-file', base_path="/my_build/subfolder")
    assert mock_patch_ng.filename.replace("\\", "/") == '/my_source/patch-file'
    assert mock_patch_ng.string is None
    assert mock_patch_ng.apply_args[0] == os.path.join("/my_build", "subfolder").replace("\\", "/")
    assert mock_patch_ng.apply_args[1] == 0
    assert mock_patch_ng.apply_args[2] is False


def test_single_patch_string(mock_patch_ng):
    conanfile = ConanFileMock()
    conanfile.folders.set_base_source("my_folder")
    conanfile.folders.set_base_export_sources("my_folder")
    conanfile.display_name = 'mocked/ref'
    output = RedirectedTestOutput()
    with redirect_output(output):
        patch(conanfile, patch_string='patch_string')
    assert mock_patch_ng.string == b'patch_string'
    assert mock_patch_ng.filename is None
    assert mock_patch_ng.apply_args == ("my_folder", 0, False)


def test_single_patch_arguments(mock_patch_ng):
    conanfile = ConanFileMock()
    conanfile.display_name = 'mocked/ref'
    conanfile.folders.set_base_source("/path/to/sources")
    conanfile.folders.set_base_export_sources("/path/to/sources")
    patch(conanfile, patch_file='patch-file', strip=23, fuzz=True)
    assert mock_patch_ng.filename.replace("\\", "/") == '/path/to/sources/patch-file'
    assert mock_patch_ng.apply_args == ("/path/to/sources", 23, True)


def test_single_patch_type(mock_patch_ng):
    output = RedirectedTestOutput()
    with redirect_output(output):
        conanfile = ConanFileMock()
        conanfile.display_name = 'mocked/ref'
        patch(conanfile, patch_file='patch-file', patch_type='patch_type')
    assert 'mocked/ref: Apply patch (patch_type)\n' == output.getvalue()


def test_single_patch_description(mock_patch_ng):
    output = RedirectedTestOutput()
    with redirect_output(output):
        conanfile = ConanFileMock()
        conanfile.display_name = 'mocked/ref'
        patch(conanfile, patch_file='patch-file', patch_description='patch_description')
    assert 'mocked/ref: Apply patch: patch_description\n' == output.getvalue()


def test_single_patch_extra_fields(mock_patch_ng):
    output = RedirectedTestOutput()
    with redirect_output(output):
        conanfile = ConanFileMock()
        conanfile.display_name = 'mocked/ref'
        patch(conanfile, patch_file='patch-file', patch_type='patch_type',
              patch_description='patch_description')
    assert 'mocked/ref: Apply patch (patch_type): patch_description\n' == output.getvalue()


def test_single_no_patchset(monkeypatch):
    with pytest.raises(ConanException) as excinfo:
        monkeypatch.setattr(patch_ng, "fromfile", lambda _: None)

        conanfile = ConanFileMock()
        conanfile.display_name = 'mocked/ref'
        patch(conanfile, patch_file='patch-file-failed')
    assert 'Failed to parse patch: patch-file-failed' == str(excinfo.value)


def test_single_apply_fail(monkeypatch):
    class MockedApply:
        def apply(self, *args, **kwargs):
            return False

    monkeypatch.setattr(patch_ng, "fromfile", lambda _: MockedApply())

    conanfile = ConanFileMock()
    conanfile.display_name = 'mocked/ref'
    with pytest.raises(ConanException) as excinfo:
        patch(conanfile, patch_file='patch-file-failed')
    assert 'Failed to apply patch: patch-file-failed' == str(excinfo.value)


class _RecordingPatchset:
    def __init__(self, calls, name):
        self._calls = calls
        self._name = name

    def apply(self, root, strip, fuzz):
        self._calls.append(("apply", self._name, root.replace("\\", "/"), strip, fuzz))
        return True


def _record_patch_ng(monkeypatch):
    calls = []

    def fromfile(filename):
        name = filename.replace("\\", "/")
        calls.append(("fromfile", name))
        return _RecordingPatchset(calls, name)

    def fromstring(string):
        calls.append(("fromstring", string))
        return _RecordingPatchset(calls, "<string>")

    monkeypatch.setattr(patch_ng, "fromfile", fromfile)
    monkeypatch.setattr(patch_ng, "fromstring", fromstring)
    return calls


_FIRST = 'patches/0001-buildflatbuffers-cmake.patch'
_SECOND = 'patches/0002-implicit-copy-constructor.patch'
_OTHER_VERSION = 'patches/0003-only-for-1.12.patch'
_BACKPORT_LINE = 'mocked/ref: Apply patch (backport): Needed to build with modern clang compilers.\n'
_BACKPORT_TEXT = 'Apply patch (backport): Needed to build with modern clang compilers.'


def _conanfile(conan_data):
    conanfile = ConanFileMock()
    conanfile.display_name = 'mocked/ref'
    conanfile.folders.set_base_source("/my_source")
    conanfile.folders.set_base_export_sources("/my_export")
    conanfile.conan_data = conan_data
    return conanfile


def _two_patches():
    return {'patches': [
        {'patch_file': _FIRST,
         'base_path': 'source_subfolder', },
        {'patch_file': _SECOND,
         'base_path': 'source_subfolder',
         'patch_type': 'backport',
         'patch_source': 'https://github.com/google/flatbuffers/pull/5650',
         'patch_description': 'Needed to build with modern clang compilers.'}
    ]}


def _applied(calls):
    return [(c[1], c[2]) for c in calls if c[0] == "apply"]


_EXPECTED_APPLIED = [('/my_export/' + _FIRST, '/my_source/source_subfolder'),
                     ('/my_export/' + _SECOND, '/my_source/source_subfolder')]


def _assert_verbose_log(log):
    # Every applied patch file can be identified in a line of the recipe output, in processing order;
    # the wording of that line is not fixed, and the existing description stays visible
    lines = log.splitlines()
    positions = []
    for name in (_FIRST, _SECOND):
        found = [i for i, line in enumerate(lines) if line.startswith('mocked/ref: ') and name in line]
        assert found, (name, log)
        positions.append(found[0])
    assert positions == sorted(positions), log
    assert _BACKPORT_TEXT in log


def test_multiple_no_version(monkeypatch):
    calls = _record_patch_ng(monkeypatch)
    # Omitted argument and explicit verbose=False keep the previous output
    for kwargs in ({}, {"verbose": False}):
        output = RedirectedTestOutput()
        with redirect_output(output):
            apply_conandata_patches(_conanfile(_two_patches()), **kwargs)
        assert _BACKPORT_LINE == output.getvalue()
    # verbose=True, as a keyword and in the position shown by the issue's signature
    for args, kwargs in (((), {"verbose": True}), ((True,), {})):
        output = RedirectedTestOutput()
        with redirect_output(output):
            apply_conandata_patches(_conanfile(_two_patches()), *args, **kwargs)
        _assert_verbose_log(output.getvalue())
    # All four calls really apply both patches (paths and base_path unchanged)
    assert _applied(calls) == _EXPECTED_APPLIED * 4


def test_multiple_with_version(monkeypatch):
    calls = _record_patch_ng(monkeypatch)
    conandata_contents = {'patches': {
        "1.11.0": [
            {'patch_file': _FIRST,
             'base_path': 'source_subfolder', },
            {'patch_file': _SECOND,
             'base_path': 'source_subfolder',
             'patch_type': 'backport',
             'patch_source': 'https://github.com/google/flatbuffers/pull/5650',
             'patch_description': 'Needed to build with modern clang compilers.'}
        ],
        "1.12.0": [
            {'patch_file': _OTHER_VERSION,
             'base_path': 'source_subfolder', },
        ]}}
    conanfile = _conanfile(copy.deepcopy(conandata_contents))

    # Previous behaviour with the argument omitted
    output = RedirectedTestOutput()
    with redirect_output(output):
        with pytest.raises(AssertionError) as excinfo:
            apply_conandata_patches(conanfile)
        assert 'Can only be applied if conanfile.version is already defined' == str(excinfo.value)
        conanfile.version = "1.2.11"
        apply_conandata_patches(conanfile)
        assert len(str(output.getvalue())) == 0
        conanfile.version = "1.11.0"
        apply_conandata_patches(conanfile)
        assert _BACKPORT_LINE == output.getvalue()

    # verbose=True: the version check is kept, a version without patches names and applies no patch
    conanfile.version = None
    with pytest.raises(AssertionError) as excinfo:
        apply_conandata_patches(conanfile, verbose=True)
    assert 'Can only be applied if conanfile.version is already defined' == str(excinfo.value)
    conanfile.version = "1.2.11"
    before = len(_applied(calls))
    output = RedirectedTestOutput()
    with redirect_output(output):
        apply_conandata_patches(conanfile, verbose=True)
    for name in (_FIRST, _SECOND, _OTHER_VERSION):
        assert name not in output.getvalue()
    assert len(_applied(calls)) == before

    # verbose=True for the matching version names and applies only that version's patches
    conanfile.version = "1.11.0"
    output = RedirectedTestOutput()
    with redirect_output(output):
        apply_conandata_patches(conanfile, verbose=True)
    log = output.getvalue()
    _assert_verbose_log(log)
    assert _OTHER_VERSION not in log
    assert _applied(calls) == _EXPECTED_APPLIED * 2

    # Ensure the function is not mutating the `conan_data` structure
    assert conanfile.conan_data == conandata_contents
