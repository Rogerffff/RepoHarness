# Reference tests rewritten to the issue contract (same test IDs as the original F2P list).
# make_revised_test_patch_v2.py inserts the helpers before test_multiple_no_version and swaps the two
# multi-patch tests in place; test_single_patch_description keeps its base (public) assertion unchanged.
# ---- helpers ----
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


# ---- test_multiple_no_version ----
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


# ---- test_multiple_with_version ----
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
