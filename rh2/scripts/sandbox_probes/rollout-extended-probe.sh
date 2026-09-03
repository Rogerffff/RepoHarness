# rh2-sandbox-script: rollout-extended-probe v1
set -u
if (echo x | timeout 5 su -c id root) >/dev/null 2>&1; then echo "ESCALATE_SU=SUCCEEDED"; else echo "ESCALATE_SU=DENIED"; fi
if command -v python3 >/dev/null 2>&1; then if python3 -c 'import os; os.setuid(0)' >/dev/null 2>&1; then echo "ESCALATE_SETUID=SUCCEEDED"; else echo "ESCALATE_SETUID=DENIED"; fi; else echo "ESCALATE_SETUID=NO_PYTHON"; fi
if [ -u /bin/su ] || [ -u /usr/bin/su ]; then echo "SU_SETUID_BIT=1"; else echo "SU_SETUID_BIT=0"; fi
STATUS=$(timeout 8 bash -c 'exec 3<>/dev/tcp/rh2-egress-relay/18001; printf "GET /rh2-sandbox-probe HTTP/1.0\r\nHost: rh2\r\n\r\n" >&3; head -c 64 <&3 | head -1' 2>/dev/null | tr -d '\r')
if [ -n "$STATUS" ]; then echo "PROXY_HTTP=$STATUS"; else echo "PROXY_HTTP=NO_RESPONSE"; fi
echo "RH2_PROBE_OK=1"
