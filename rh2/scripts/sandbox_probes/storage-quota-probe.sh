# rh2-sandbox-script: storage-quota-probe v1
set -u
TARGET=$(( 8589934592 + 67108864 ))
if ! command -v fallocate >/dev/null 2>&1; then echo "QUOTA_ENFORCED=UNKNOWN_NO_FALLOCATE"; exit 0; fi
if fallocate -l "$TARGET" /rh2_quota_probe.bin 2>/dev/null; then rm -f /rh2_quota_probe.bin; echo "QUOTA_ENFORCED=0"; else rm -f /rh2_quota_probe.bin; echo "QUOTA_ENFORCED=1"; fi
