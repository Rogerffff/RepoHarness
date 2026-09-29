#!/bin/bash
PYTHONDONTWRITEBYTECODE=1 python -c "
from datalad.interface.tests.test_utils import Test_Utils
from datalad.distribution.dataset import Dataset
seen = {}
def spy(tag):
    def f(res, **kwargs):
        seen.setdefault(tag, sorted(kwargs))
        return True
    return f
call = Test_Utils().__call__
call(1, dataset='awesome', result_filter=spy('kw_dataset'))
list(call(1, dataset='awesome', return_type='generator', result_filter=spy('kw_dataset_generator')))
call(1, 'awesome', result_filter=spy('positional_dataset'))
call(1, result_filter=spy('no_dataset'))
Dataset('/does/not/matter').fake_command(1, result_filter=spy('dataset_method'))
for k in sorted(seen):
    print(k, seen[k])
"
echo RH2_CMD_RC=$?
