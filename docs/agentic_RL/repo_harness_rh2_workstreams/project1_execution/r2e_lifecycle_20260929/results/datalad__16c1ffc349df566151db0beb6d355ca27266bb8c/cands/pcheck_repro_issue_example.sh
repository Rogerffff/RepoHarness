#!/bin/bash
PYTHONDONTWRITEBYTECODE=1 python -c "
from datalad.interface.tests.test_utils import Test_Utils
def custom_filter(res, **kwargs):
    assert 'dataset' in kwargs, 'FILTER_KWARGS=%r' % (kwargs,)
    return True
out = Test_Utils().__call__(4, dataset='awesome', result_filter=custom_filter)
print('RESULT', [r['somekey'] for r in out])
"
echo RH2_CMD_RC=$?
