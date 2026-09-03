# rh2-sandbox-script: grader-chown-before-eval v1
set -u
chown -R 54322:54322 /testbed || { echo "RH2_CHOWN_ERROR=1"; exit 4; }
echo "RH2_CHOWN_OK=1"
