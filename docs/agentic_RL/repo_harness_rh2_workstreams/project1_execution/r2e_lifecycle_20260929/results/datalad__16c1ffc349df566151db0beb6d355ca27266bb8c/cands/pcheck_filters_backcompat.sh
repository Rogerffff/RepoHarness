#!/bin/bash
PYTHONDONTWRITEBYTECODE=1 python -c "
from datalad.interface.tests.test_utils import Test_Utils
from datalad.distribution.dataset import Dataset
from datalad.support.constraints import EnsureKeyChoice
keys = lambda rs: [r['somekey'] for r in rs]
call = Test_Utils().__call__
ds = Dataset('/does/not/matter')
checks = [
    ('keychoice', keys(call(4, dataset='awesome', result_filter=EnsureKeyChoice('somekey', (0, 2)))), [0, 2]),
    ('and_constraints', keys(call(4, dataset='awesome', result_filter=EnsureKeyChoice('status', ('ok',)) & EnsureKeyChoice('somekey', (1, 3)))), [1, 3]),
    ('one_arg_lambda', keys(call(4, dataset='awesome', result_filter=lambda x: x['somekey'] in (0, 2))), [0, 2]),
    ('generator_mode', keys(call(4, dataset='awesome', return_type='generator', result_filter=EnsureKeyChoice('somekey', (0, 2)))), [0, 2]),
    ('dataset_method_constraint', keys(ds.fake_command(4, result_filter=EnsureKeyChoice('somekey', (0, 2)))), [0, 2]),
    ('dataset_method_lambda', keys(ds.fake_command(4, result_filter=lambda x: x['somekey'] in (0, 2))), [0, 2]),
]
for name, got, want in checks:
    print(name, got)
    assert got == want, (name, got, want)
print('BACKCOMPAT_OK')
"
echo RH2_CMD_RC=$?
