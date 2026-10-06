Work in `/testbed` using the existing `/testbed/.venv`. Use the installed
dependencies; external network access is disabled. Edit non-test source files
and leave the repository's tests intact.

This checkout includes compiled Cython extensions. If you change a `.pyx`
source, rebuild the extensions before testing the change:

```bash
python setup.py build_ext --inplace
```

Check the build's exit status and output. Use a new Python process to check
the imported extension's path and to reproduce the issue; changing the source
alone does not update an already-built extension. Do not assume an old binary
or a module already loaded in a Python process reflects the source edit.

The issue provides a small reproduction. Inspect the actual returned points
and interval behavior, rather than treating an exception-catching script's
zero exit status as proof of success. The public repository also includes
these narrow regression checks:

```bash
QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum python -m pytest -q \
  Orange/tests/test_discretize.py::TestEqualFreq
```

That class covers ordinary equal-frequency discretization and inputs with
fewer distinct values than the requested number of bins. Its success alone
does not establish that the near-identical-value issue is fixed. Check the
issue's behavior and preserve the existing public discretization contract.

This brief gives development commands and public check locations. It does
not report that the whole public test file has passed. Summarize your source
change and the checks you performed when you finish.
