#!/bin/bash
cd /testbed && env | grep -i '^PYTHONWARNINGS' ; python -c "import sys; print(sys.warnoptions)"
echo RH2_CMD_RC=$?
