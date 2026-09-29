# Reference tests rewritten to the issue contract (same test IDs as the original F2P list).
# make_revised_test_patch.py swaps these in for the same-named functions of the base test file.


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
_BACKPORT_LINE = 'mocked/ref: Apply patch (backport): Needed to build with modern clang compilers.\n'


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


def _verbose_log_positions(log):
    lines = log.splitlines()
    positions = []
    for name in (_FIRST, _SECOND):
        found = [i for i, line in enumerate(lines) if line.startswith('mocked/ref: ') and name in line]
        assert found, (name, log)
        positions.append(found[0])
    return positions


def test_single_patch_description(mock_patch_ng):
    # Direct patch() output is unchanged: the issue only adds a switch to apply_conandata_patches
    output = RedirectedTestOutput()
    with redirect_output(output):
        conanfile = ConanFileMock()
        conanfile.display_name = 'mocked/ref'
        patch(conanfile, patch_file='patch-file', patch_description='patch_description')
    assert 'mocked/ref: Apply patch: patch_description\n' == output.getvalue()


def test_multiple_no_version(monkeypatch):
    calls = _record_patch_ng(monkeypatch)
    # Omitted argument and explicit verbose=False: the previous output, no list of patch files
    for kwargs in ({}, {"verbose": False}):
        output = RedirectedTestOutput()
        with redirect_output(output):
            apply_conandata_patches(_conanfile(_two_patches()), **kwargs)
        assert _BACKPORT_LINE == output.getvalue()
    # verbose=True (keyword and positional): every applied patch file is identifiable in the output, in order
    for args, kwargs in (((), {"verbose": True}), ((True,), {})):
        output = RedirectedTestOutput()
        with redirect_output(output):
            apply_conandata_patches(_conanfile(_two_patches()), *args, **kwargs)
        log = output.getvalue()
        positions = _verbose_log_positions(log)
        assert positions == sorted(positions), log
        assert _BACKPORT_LINE in log
    # All four calls really apply both patches (paths and base_path unchanged)
    assert _applied(calls) == _EXPECTED_APPLIED * 4


def test_multiple_with_version(monkeypatch):
    calls = _record_patch_ng(monkeypatch)
    output = RedirectedTestOutput()
    with redirect_output(output):
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
                {'patch_file': 'patches/0003-only-for-1.12.patch',
                 'base_path': 'source_subfolder', },
            ]}}
        conanfile = _conanfile(copy.deepcopy(conandata_contents))

        with pytest.raises(AssertionError) as excinfo:
            apply_conandata_patches(conanfile, verbose=True)
        assert 'Can only be applied if conanfile.version is already defined' == str(excinfo.value)

        conanfile.version = "1.2.11"
        apply_conandata_patches(conanfile, verbose=True)
        assert len(str(output.getvalue())) == 0

        conanfile.version = "1.11.0"
        apply_conandata_patches(conanfile)
        assert _BACKPORT_LINE == output.getvalue()

    output = RedirectedTestOutput()
    with redirect_output(output):
        apply_conandata_patches(conanfile, verbose=True)
    log = output.getvalue()
    positions = _verbose_log_positions(log)
    assert positions == sorted(positions), log
    assert 'patches/0003-only-for-1.12.patch' not in log
    assert _BACKPORT_LINE in log
    assert _applied(calls) == _EXPECTED_APPLIED * 2

    # Ensure the function is not mutating the `conan_data` structure
    assert conanfile.conan_data == conandata_contents
