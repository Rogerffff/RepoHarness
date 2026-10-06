Work in `/testbed` using the existing `/testbed/.venv`. The preparation check
used Python 3.7.9 and NumPy 1.17.5, and imported Orange from the checked-out
repository. Use the installed dependencies; external network access is disabled.
Edit non-test source files and leave the repository's tests intact.

Use headless Qt for widget imports and tests. These existing public regression
selectors were run successfully on the original implementation:

```bash
QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum python -m pytest -q \
  Orange/widgets/data/tests/test_owcolor.py::TestOWColor::test_parse_var_defs \
  Orange/widgets/data/tests/test_owcolor.py::TestOWColor::test_parse_var_defs_invalid \
  Orange/widgets/data/tests/test_owcolor.py::TestOWColor::test_parse_var_defs_shows_warnings \
  Orange/widgets/data/tests/test_owcolor.py::TestOWColor::test_load \
  Orange/widgets/data/tests/test_owcolor.py::DiscAttrTest::test_to_dict
```

Their success alone does not establish that the issue is fixed. Check the
warning behavior requested in the issue with temporary assertions, including
unused definitions from either section, and preserve the existing behavior for
valid definitions and renames. Temporary checks can use the public widget test
fixtures without changing the repository's tests.

The issue's Development Note identifies a conflict in this existing public
method:

```bash
QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum python -m pytest -q \
  Orange/widgets/data/tests/test_owcolor.py::TestOWColor::test_parse_var_defs_no_rename
```

Its earlier duplicate-rename and name-swap checks remain useful. Its final
assertion requires no warning for an unused definition, which conflicts with
this issue's requested warning. Keep the test unchanged, inspect the actual
failure location, and check that final case against the issue instead of
suppressing the requested warning to make the old assertion pass.

The preparation check ran the five selectors above and the whole conflict
method. It did not run the entire public test file. Summarize the source change
and the checks you performed when you finish.
