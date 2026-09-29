#!/bin/bash
cd /testbed && PYTHONDONTWRITEBYTECODE=1 python -c "import numpy as np; np.histogram2d([1,2,3],[1,2,3],bins=[[1,2,3,5],[1,2,3,5]],normed=True); np.histogramdd(np.c_[[1,2,3],[1,2,3]],bins=[[1,2,3,5],[1,2,3,5]],normed=True); print('normed ok')"
echo RH2_CMD_RC=$?
