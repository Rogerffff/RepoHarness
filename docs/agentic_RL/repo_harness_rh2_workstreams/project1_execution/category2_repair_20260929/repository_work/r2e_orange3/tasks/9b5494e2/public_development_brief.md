Work in `/testbed` using the existing `/testbed/.venv`. The prepared environment
uses Python 3.7.9, NumPy 1.17.5, SciPy 1.5.4, and scikit-learn 0.22.2.post1.
Use these installed dependencies; external network access is disabled. Edit
non-test source files and leave the repository's tests intact.

The issue can be reproduced by fitting the public learner on the bundled iris
dataset:

```python
from Orange.data import Table
from Orange.classification import LogisticRegressionLearner

iris_data = Table("iris")
model = LogisticRegressionLearner(penalty="l1")(iris_data)
```

Check actual fitting, not only successful learner construction. Investigate
the installed library's supported options and the repository's current
behavior. The requested automatic handling of the penalty should preserve
existing behavior for configurations that already work.

These public test selectors cover the default learner and the probability
output of a learner configured with `penalty="l1"`:

```bash
python -m pytest -q \
  Orange/tests/test_logistic_regression.py::TestLogisticRegressionLearner::test_LogisticRegression \
  Orange/tests/test_logistic_regression.py::TestLogisticRegressionLearner::test_probability
```

The L1 probability test may expose the same issue on the original
implementation. Passing these checks alone does not establish that the issue
is fixed. Verify
the requested L1 fit and relevant existing configurations with narrow public
or temporary checks. This brief does not claim that the entire public test
file has passed. Summarize the source change and the checks you performed
when you finish.
