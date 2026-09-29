# Test methods with long descriptive names can omit docstrings
# pylint: disable=missing-docstring

import unittest

from Orange.classification import LogisticRegressionLearner


class TestLogisticRegressionDefaultRepr(unittest.TestCase):
    def test_default_learner_repr(self):
        # Same check as the public Orange/tests/test_util.py
        # (TestUtil.test_reprable, "GH 2275"): the default learner has an
        # argument-free repr, also when repr is called repeatedly
        logit = LogisticRegressionLearner()
        for _ in range(2):
            self.assertEqual(repr(logit), 'LogisticRegressionLearner()')
