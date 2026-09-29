import numpy as np
a = np.ma.arange(500); a[1:50] = np.ma.masked; s = str(a); t = s.replace('[', ' ').replace(']', ' ').split()
print('n500', len(t), '...' in s, t == ['0'] + ['--'] * 49 + [str(i) for i in range(50, 500)])
a = np.ma.arange(100000); a[-2:] = np.ma.masked; s = str(a)
print('n1e5', s == '[0 1 2 ..., 99997 -- --]', len(s.split()))
