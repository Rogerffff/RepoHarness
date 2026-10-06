#!/usr/bin/env python3
"""在本题真实容器内定向核行为；不是正式评分。本地准备阶段不执行。"""

import json
import sys


def main():
    if sys.version_info[:2] != (3, 7):
        raise SystemExit("请在本题 /testbed/.venv Python 3.7 容器内执行，不使用宿主 NumPy")
    import numpy as np

    if not np.__file__.startswith('/testbed/numpy/'):
        raise SystemExit("必须从本题 /testbed/numpy 导入")
    original_options = np.get_printoptions()
    results = []
    scenarios = [
        ('default_summary', 100000, 1000, 3, 'tail'),
        ('default_full', 500, 1000, 3, 'head'),
        ('raised_full', 2000, 2000, 3, 'head'),
        ('raised_summary', 3000, 2000, 3, 'head'),
        ('large_edgeitems', 3000, 1000, 501, 'head'),
    ]
    try:
        for name, size, threshold, edgeitems, mask_location in scenarios:
            np.set_printoptions(**original_options)
            np.set_printoptions(threshold=threshold, edgeitems=edgeitems)
            a = np.ma.arange(size)
            if mask_location == 'tail':
                a[-2:] = np.ma.masked
                values = [str(i) for i in range(size - 2)] + ['--', '--']
            else:
                a[1:50] = np.ma.masked
                values = ['0'] + ['--'] * 49 + [str(i) for i in range(50, size)]
            if size > threshold and size > 2 * edgeitems:
                expected = values[:edgeitems] + ['...'] + values[-edgeitems:]
            else:
                expected = values
            output = str(a)
            observed = output.replace('[', ' ').replace(']', ' ').replace(',', ' ').split()
            results.append({'scenario': name, 'size': size, 'threshold': threshold,
                            'edgeitems': edgeitems, 'match': observed == expected,
                            'expected_tokens': len(expected), 'observed_tokens': len(observed),
                            'has_ellipsis': '...' in observed, 'output': output})
    finally:
        np.set_printoptions(**original_options)
    print(json.dumps({'kind': 'private_behavior_check_not_formal_score',
                      'python': sys.version, 'numpy': np.__version__,
                      'numpy_file': np.__file__, 'results': results,
                      'all_match': all(r['match'] for r in results)}, indent=2))
    return 0 if all(r['match'] for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
