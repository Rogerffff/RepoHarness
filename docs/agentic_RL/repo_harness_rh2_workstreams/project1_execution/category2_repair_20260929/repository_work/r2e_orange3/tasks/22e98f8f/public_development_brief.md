Work in `/testbed`. Use the existing task virtual environment at
`/testbed/.venv`; `python` should resolve to `/testbed/.venv/bin/python`.
This environment has Python 3.7.9 and NumPy 1.17.5. Orange imports from the
checked-out repository. There is no external network access; use the installed
dependencies. Edit non-test source files and leave the repository's tests intact.

The module imports widget dependencies. Use the following headless Qt prefix
for imports and tests:

```bash
QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum python -m pytest -q Orange/widgets/data/tests/test_owcreateclass.py::TestHelpers::test_unique_in_order_mapping
```

This existing test passes on the original implementation, so its success alone
does not establish that the mapping is correct for general input. You can check
the issue's reconstruction relation with temporary assertions without editing
test files:

```bash
QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum python - <<'PY'
import numpy as np
from Orange.widgets.data.owcreateclass import unique_in_order_mapping

for values in ([8, 4, 6, 8, 4],
               ["zebra", "apple", "zebra", "mint", "apple"]):
    unique, mapping = unique_in_order_mapping(values)
    unique, mapping = np.asarray(unique), np.asarray(mapping)
    assert unique[mapping].tolist() == values
PY
```

The original implementation fails the first assertion. The loop stops at that
failure; run either example separately if you want to inspect both. Preserve
first-appearance order and the mapping behavior described in the issue.

For a broader check of the existing call sites, the same public test file can
be run with:

```bash
QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum python -m pytest -q Orange/widgets/data/tests/test_owcreateclass.py
```

Only the helper test and the first reconstruction example have been executed
in the current preparation check; this note does not assert that the full file
already passes. Summarize the source change and the checks you performed when
you finish.
