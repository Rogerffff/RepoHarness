#!/bin/bash
cd /testbed && PYTHONDONTWRITEBYTECODE=1 python -c "import numpy as np; H,xe,ye=np.histogram2d([0.5,1.5,2.5,9.0],[0.5,1.5,2.5,9.0],bins=3,range=[[0,3],[0,3]],density=True); I=(H*np.outer(np.diff(xe),np.diff(ye))).sum(); print('integral', I); assert abs(I-1)<1e-12"
echo RH2_CMD_RC=$?
