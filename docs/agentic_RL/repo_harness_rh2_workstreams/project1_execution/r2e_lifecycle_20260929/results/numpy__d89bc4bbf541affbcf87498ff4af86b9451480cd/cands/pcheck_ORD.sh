#!/bin/bash
cd /testbed && PYTHONDONTWRITEBYTECODE=1 python -c "import numpy as np; v=np.arange(10); b=np.array([0,1,3,6,10]); dd=np.histogramdd((v,),(b,),density=True)[0]; h=np.histogram(v,b,density=True)[0]; print(dd.tolist(), h.tolist()); assert np.allclose(dd,h); print('bitwise_equal', bool((dd==h).all()))"
echo RH2_CMD_RC=$?
